import os
import cv2
import numpy as np
from rembg import remove, new_session
from PIL import Image, ImageOps
from tqdm import tqdm

# --- CONFIGURATION ---
RAW_DIR = "my_wardrobe/raw"
PROCESSED_DIR = "my_wardrobe/data"

# FIX 1: Switch to a model trained on humans/clothes, not general objects
# 'u2net_human_seg' ignores furniture/blankets better than 'isnet'
print("Loading Robust Model (u2net_human_seg)...")
session = new_session("u2net_human_seg") 

def get_largest_contour_mask(pil_img):
    """
    Computer Vision Pass:
    Finds the biggest 'blob' in the image and deletes everything else.
    """
    # Convert to standard OpenCV format
    img = np.array(pil_img)
    
    # Extract Alpha (Transparency) Channel
    if img.shape[2] != 4: return pil_img
    alpha = img[:, :, 3]
    
    # Threshold: Make sure pixels are either 0 (transparent) or 255 (opaque)
    _, binary = cv2.threshold(alpha, 127, 255, cv2.THRESH_BINARY)
    
    # Find all shapes
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours: return pil_img

    # Find the single biggest shape (The Garment)
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Create a clean mask: Black background, White garment
    mask = np.zeros_like(binary)
    cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
    
    # Apply this mask to the alpha channel
    img[:, :, 3] = mask
    
    return Image.fromarray(img)

def clean_image_robust(pil_image):
    """Clean image by removing background - accepts PIL Image object"""
    try:
        input_img = ImageOps.exif_transpose(pil_image) # Fix rotation bugs
        
        # FIX 2: Disable Alpha Matting
        # Alpha matting causes the "Ghosting" on white shirts. 
        # Clothes have hard edges, so we don't need it.
        ai_clean = remove(
            input_img, 
            session=session,
            alpha_matting=False  # <--- CRITICAL CHANGE
        )
        
        # FIX 3: Geometric Cleanup
        # Removes the floating "blanket islands"
        final_clean = get_largest_contour_mask(ai_clean)
        
        return final_clean
        
    except Exception as e:
        print(f"Error on {image_path}: {e}")
        return None

def main():
    # Setup Output Folders
    out_dir = os.path.join(PROCESSED_DIR, "images")
    os.makedirs(out_dir, exist_ok=True)
    
    files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"🚀 Starting Robust Clean on {len(files)} images...")
    
    for filename in tqdm(files):
        raw_path = os.path.join(RAW_DIR, filename)
        
        clean_img = clean_image_robust(raw_path)
        
        if clean_img:
            # Save as PNG
            base_name = os.path.splitext(filename)[0]
            out_path = os.path.join(out_dir, f"{base_name}_clean.png")
            clean_img.save(out_path)

    print(f"\n✅ Done. Check {out_dir}")

if __name__ == "__main__":
    main()