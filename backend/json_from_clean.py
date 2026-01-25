import os
import json
import time
from PIL import Image
import google.generativeai as genai
from tqdm import tqdm

# Try to import FashionCLIP, but make it optional
try:
    from fashion_clip.fashion_clip import FashionCLIP
    FASHION_CLIP_AVAILABLE = True
except ImportError:
    print("⚠️ FashionCLIP not available - style tags will be skipped")
    FASHION_CLIP_AVAILABLE = False

# --- CONFIGURATION ---
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or "YOUR_KEY_HERE"

# Folder Paths
# This should point to where your clean PNGs are currently located
CLEAN_IMAGES_DIR = "my_wardrobe/data/images" 
# This is where the JSON files will be saved
JSON_OUTPUT_DIR = "my_wardrobe/data/json"

# --- INITIALIZATION ---
print("🔧 Initializing System...")

# 1. Setup Gemini
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_KEY_HERE" and GEMINI_API_KEY != "YOUR_NEW_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("⚠️ Warning: No valid Gemini API key found. Please set GEMINI_API_KEY in .env file")
    print("   Get a new API key from: https://makersuite.google.com/app/apikey")
    model = None

# 2. Setup FashionCLIP (optional)
if FASHION_CLIP_AVAILABLE:
    print("👗 Loading FashionCLIP model...")
    fclip = FashionCLIP('fashion-clip')
else:
    fclip = None

def extract_tags_gemini(pil_image):
    """Stage 2: Attribute Extraction"""
    
    # Check if Gemini is configured
    if model is None:
        print("⚠️ Gemini not configured - returning placeholder attributes")
        return {
            "category": "Unknown",
            "sub_category": "Unknown",
            "primary_color": "Unknown",
            "secondary_colors": [],
            "pattern": "Unknown",
            "material_appearance": "Unknown",
            "seasonality": "All-Season",
            "formality": "Casual",
            "error": "Gemini API key not configured"
        }
    
    prompt = """
    Analyze this clothing item. Return a strict JSON object with these keys:
    - category: (Top, Bottom, Footwear, Outerwear, One-Piece, Accessory)
    - sub_category: (e.g. Hoodie, Chinos, Chelsea Boots)
    - primary_color: (string)
    - secondary_colors: (list of strings)
    - pattern: (Solid, Striped, Floral, Logo, etc.)
    - material_appearance: (e.g. Denim, Cotton, Leather, Knit)
    - seasonality: (Summer, Winter, All-Season)
    - formality: (Casual, Smart-Casual, Formal)
    """
    
    try:
        # Generate content
        response = model.generate_content([prompt, pil_image])
        
        # Clean response text
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return {
            "category": "Unknown", 
            "error": str(e)
        }

def get_fashion_vector(image_path):
    """Stage 3: Vector Embedding"""
    if not FASHION_CLIP_AVAILABLE or fclip is None:
        print("⚠️ FashionCLIP not available, skipping vector embedding")
        return []
    
    try:
        # FashionCLIP reads from file path
        embeddings = fclip.encode_images([image_path], batch_size=1)
        return embeddings[0].tolist()
    except Exception as e:
        print(f"⚠️ Vector Error: {e}")
        return []

def main():
    # Ensure JSON directory exists
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

    # Check if input directory exists
    if not os.path.exists(CLEAN_IMAGES_DIR):
        print(f"❌ Error: Clean directory not found at {CLEAN_IMAGES_DIR}")
        return

    valid_exts = ('.jpg', '.jpeg', '.png', '.webp')
    files = [f for f in os.listdir(CLEAN_IMAGES_DIR) if f.lower().endswith(valid_exts)]
    
    print(f"🚀 Processing metadata for {len(files)} images...\n")

    for filename in tqdm(files, desc="Tagging & Embedding"):
        clean_img_path = os.path.join(CLEAN_IMAGES_DIR, filename)
        base_name = os.path.splitext(filename)[0].replace("_clean", "") # Clean up filename if needed
        
        # Open image for Gemini
        try:
            pil_img = Image.open(clean_img_path)
        except Exception as e:
            print(f"Skipping {filename}: {e}")
            continue

        # --- STEP 1: TAG (Gemini) ---
        tags = extract_tags_gemini(pil_img)
        
        # --- STEP 2: EMBED (FashionCLIP) ---
        vector = get_fashion_vector(clean_img_path)

        # --- STEP 3: SAVE JSON ---
        asset_record = {
            "id": base_name,
            "timestamp": time.time(),
            "meta": tags,
            "embedding": vector,
            "paths": {
                "clean": clean_img_path
                # "raw": raw_path # Removed as we might not know the raw path here
            }
        }

        json_path = os.path.join(JSON_OUTPUT_DIR, f"{base_name}.json")
        with open(json_path, 'w') as f:
            json.dump(asset_record, f, indent=2)

    print(f"\n✅ Processing Complete. JSONs saved to {JSON_OUTPUT_DIR}")

if __name__ == "__main__":
    main()