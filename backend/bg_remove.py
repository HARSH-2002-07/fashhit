import os
import sys
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

import cv2
import numpy as np
from rembg import remove, new_session
from PIL import Image, ImageOps

# Optional: AVIF support (install with: pip install pillow-avif)
try:
    import pillow_avif
except ImportError:
    pass  # AVIF files won't be supported without this

# --- CONFIGURATION ---
RAW_DIR = Path("my_wardrobe/raw")
PROCESSED_DIR = Path("my_wardrobe/data")
OUTPUT_SIZE = 512

# UPDATED: Added .avif, .webp, .jpeg (and typical variations)
VALID_EXTENSIONS = frozenset([
    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.avif', '.tiff'
])
MAX_WORKERS = 4 

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Global session to prevent reloading model 4x times
_SESSION = None

def get_session():
    global _SESSION
    if _SESSION is None:
        logger.info("⏳ Loading AI Model (u2net_human_seg)...")
        _SESSION = new_session("u2net_human_seg")
    return _SESSION

class ImageProcessor:
    def __init__(self):
        # Kernels for morphological operations
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    
    def remove_halo_and_smooth(self, img_array: np.ndarray) -> np.ndarray:
        """
        The 'Sticker' Effect:
        1. Erode (Shrink) mask by 1px to cut off background fringe.
        2. Blur mask by 3px to soften the jagged edges.
        """
        if img_array.shape[2] != 4: return img_array
        
        alpha = img_array[:, :, 3]
        
        # 1. Threshold to remove weak transparent noise
        _, binary = cv2.threshold(alpha, 127, 255, cv2.THRESH_BINARY)
        
        # 2. Erode: Shave off 1 pixel from the edge to remove "Background Halo"
        # This is safer and cleaner than alpha matting for clothes
        eroded = cv2.erode(binary, np.ones((3,3), np.uint8), iterations=1)
        
        # 3. Soften: Apply Gaussian Blur to the alpha channel only
        # This gives a nice anti-aliased edge
        soft_alpha = cv2.GaussianBlur(eroded, (3, 3), 0)
        
        img_array[:, :, 3] = soft_alpha
        return img_array

    def keep_largest_object(self, img_array: np.ndarray) -> np.ndarray:
        """
        Removes 'islands' of noise (dust, shadows) by keeping only the 
        largest connected object (the garment).
        """
        alpha = img_array[:, :, 3]
        _, binary = cv2.threshold(alpha, 127, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return img_array

        # Sort contours by area
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        largest_cnt = contours[0]
        
        # Create a fresh mask with ONLY the largest object
        new_mask = np.zeros_like(alpha)
        cv2.drawContours(new_mask, [largest_cnt], -1, 255, thickness=cv2.FILLED)
        
        # Also keep 2nd largest if it's significant (e.g. a detached belt or shoe)
        if len(contours) > 1:
            second_cnt = contours[1]
            if cv2.contourArea(second_cnt) > (cv2.contourArea(largest_cnt) * 0.1):
                 cv2.drawContours(new_mask, [second_cnt], -1, 255, thickness=cv2.FILLED)

        img_array[:, :, 3] = new_mask
        return img_array

    def center_on_canvas(self, pil_img: Image.Image, output_size: int) -> Image.Image:
        """
        Locates the garment, crops it tight, and centers it on the square canvas.
        Essential for Vector Embedding accuracy.
        """
        img_array = np.array(pil_img)
        alpha = img_array[:, :, 3]
        
        # Find Bounding Box of the actual pixels
        coords = cv2.findNonZero(alpha)
        if coords is None: return pil_img.resize((output_size, output_size))
        
        x, y, w, h = cv2.boundingRect(coords)
        
        # Crop tight to the object
        crop = pil_img.crop((x, y, x+w, y+h))
        
        # Calculate resize factor (Fit to 90% of canvas)
        target_dim = int(output_size * 0.90)
        max_dim = max(w, h)
        scale = target_dim / max_dim
        
        new_w, new_h = int(w * scale), int(h * scale)
        crop_resized = crop.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Paste into center
        final_img = Image.new('RGBA', (output_size, output_size), (0, 0, 0, 0))
        paste_x = (output_size - new_w) // 2
        paste_y = (output_size - new_h) // 2
        
        final_img.paste(crop_resized, (paste_x, paste_y), crop_resized)
        return final_img

    def process_image(self, image_path: Path) -> Optional[Image.Image]:
        try:
            # .convert('RGB') handles RGBA (png) and Palette (gif/png) modes gracefully
            img = Image.open(image_path).convert("RGB")
            img = ImageOps.exif_transpose(img) # Fix rotation
            
            # 1. AI Segmentation (Fast Mode)
            # alpha_matting=False is PREFERRED for clothes to avoid ghosting
            session = get_session()
            bg_removed = remove(img, session=session, alpha_matting=False)
            
            img_array = np.array(bg_removed)
            
            # 2. Cleanup: Remove dust/shadows
            img_array = self.keep_largest_object(img_array)
            
            # 3. Polish: Remove Halo & Smooth Edges
            img_array = self.remove_halo_and_smooth(img_array)
            
            # 4. Format: Center & Resize
            result_img = Image.fromarray(img_array)
            final_img = self.center_on_canvas(result_img, OUTPUT_SIZE)
            
            return final_img
            
        except Exception as e:
            logger.error(f"❌ Error on {image_path.name}: {e}")
            return None

# --- WORKER ---
def worker(args):
    path, proc, out_dir = args
    res = proc.process_image(path)
    if res:
        # Save as PNG to preserve transparency
        res.save(out_dir / f"{path.stem}_clean.png", "PNG")
        return True
    return False

def main():
    out_dir = PROCESSED_DIR / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not RAW_DIR.exists():
        logger.error(f"❌ Missing folder: {RAW_DIR}")
        return

    # Filter files that match our expanded VALID_EXTENSIONS list
    files = sorted([f for f in RAW_DIR.iterdir() if f.suffix.lower() in VALID_EXTENSIONS])
    
    if not files:
        logger.error(f"⚠️ No valid images found in {RAW_DIR}. Supported: {VALID_EXTENSIONS}")
        return

    logger.info(f"🚀 Found {len(files)} images. Starting {MAX_WORKERS} threads...")
    
    # Init Processor & Model once
    processor = ImageProcessor()
    get_session() 
    
    tasks = [(f, processor, out_dir) for f in files]
    success = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(worker, t): t[0] for t in tasks}
        
        for i, fut in enumerate(as_completed(futures)):
            path = futures[fut]
            try:
                if fut.result():
                    success += 1
                    print(f"[{i+1}/{len(files)}] ✅ {path.name}", end="\r")
                else:
                    print(f"[{i+1}/{len(files)}] ❌ {path.name}", end="\r")
            except Exception as e:
                logger.error(f"\nCrash {path.name}: {e}")
                
    print(f"\n✨ Done. {success}/{len(files)} processed.")

if __name__ == "__main__":
    main()