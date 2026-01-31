import os
import json
import numpy as np
from PIL import Image
from fashion_clip.fashion_clip import FashionCLIP
from tqdm import tqdm

# --- CONFIGURATION ---
DATA_DIR = "my_wardrobe/data"  # Point to your actual data folder
JSON_DIR = os.path.join(DATA_DIR, "json")

# --- DEFINITIONS ---
# We define the concepts we want to detect
ATTRIBUTES = {
    "fit": ["Oversized fit", "Relaxed fit", "Regular fit", "Slim fit", "Skinny fit"],
    "cut": ["Cropped length", "Standard length", "Long length", "Ankle length"],
    "occasion": ["Casual daily wear", "Formal business wear", "Party night out", "Gym athletic wear", "Beach summer wear"]
}

def classify_attribute(fclip, image_path, options):
    """
    Uses FashionCLIP to find which text option matches the image best.
    """
    try:
        # 1. Encode the Image
        # (In a real pipeline, we would cache this, but it's fast enough)
        img_vec = fclip.encode_images([image_path], batch_size=1)[0]
        
        # 2. Encode the Text Options
        text_vecs = fclip.encode_text(options, batch_size=len(options))
        
        # 3. Calculate Similarity (Dot Product)
        # Normalize vectors first for Cosine Similarity
        img_vec /= np.linalg.norm(img_vec)
        text_vecs = text_vecs / np.linalg.norm(text_vecs, axis=1, keepdims=True)
        
        scores = np.dot(text_vecs, img_vec)
        
        # 4. Pick Winner
        best_idx = np.argmax(scores)
        
        # Clean the tag (remove " fit" or " length" for cleaner metadata)
        winner = options[best_idx]
        clean_tag = winner.replace(" fit", "").replace(" length", "").replace(" wear", "").split()[0]
        
        return clean_tag.capitalize()
        
    except Exception as e:
        print(f"Error classifying {image_path}: {e}")
        return "Regular" # Default fallback

def main():
    print("🧠 Loading FashionCLIP (Local Brain)...")
    fclip = FashionCLIP('fashion-clip')
    
    files = [f for f in os.listdir(JSON_DIR) if f.endswith(".json")]
    print(f"🚀 Upgrading {len(files)} items with Silhouette Logic...\n")
    
    updated_count = 0
    
    for filename in tqdm(files):
        path = os.path.join(JSON_DIR, filename)
        
        with open(path, "r") as f:
            data = json.load(f)
            
        # Get image path
        img_path = data['paths']['clean']
        if not os.path.exists(img_path):
            # Try to fix path if moved
            base = os.path.basename(img_path)
            img_path = os.path.join(DATA_DIR, "images", base)
            if not os.path.exists(img_path):
                print(f"⚠️ Image missing for {filename}, skipping.")
                continue
        
        # --- LOCAL CLASSIFICATION ---
        # 1. Detect Fit
        fit = classify_attribute(fclip, img_path, ATTRIBUTES["fit"])
        
        # 2. Detect Cut (Only relevant for Tops/Bottoms/Outerwear)
        cut = "Standard"
        if data['meta']['category'] in ['Top', 'Bottom', 'Outerwear']:
            cut = classify_attribute(fclip, img_path, ATTRIBUTES["cut"])

        # Normalize cut BEFORE saving
        if cut == "Ankle":
            cut = "Cropped"

        data['meta']['length_profile'] = cut

        # 3. Detect Occasion
        occasion = classify_attribute(fclip, img_path, ATTRIBUTES["occasion"])
        
        # --- UPDATE JSON ---
        # We preserve existing metadata and just inject new fields
        if data['meta'].get('fit') in [None, "Regular"]:
            data['meta']['fit'] = fit

        data['meta']['cut'] = cut
        # Merge visual confirmation into existing occasion list
        if 'occasion' not in data['meta'] or not isinstance(data['meta']['occasion'], list):
            data['meta']['occasion'] = []

        if occasion not in data['meta']['occasion']:
            data['meta']['occasion'].append(occasion)
 # 'occasion' is a reserved list in some schemas
        
        # Save back to disk
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            
        updated_count += 1

    print(f"\n✅ Success! Upgraded {updated_count} items.")
    print("   Now run planner_v5.py (It will automatically read these new tags).")

if __name__ == "__main__":
    main()