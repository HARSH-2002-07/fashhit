import os
import time
import requests
from ddgs import DDGS
from PIL import Image
from io import BytesIO

ROOT_DIR = "raw"
IMAGES_PER_ITEM = 3
REQUEST_DELAY = 2.5  # seconds (prevents rate limit)

WARDROBE = {

    # ======================
    # TOPS
    # ======================

    "Tshirts": {
        "Crew_Neck_Tshirt": [
            "white", "black", "navy", "charcoal", "olive"
        ],
        "Oversized_Tshirt": [
            "washed black", "stone", "sand", "muted olive"
        ],
        "V_Neck_Tshirt": [
            "white", "grey", "navy"
        ],
        "Striped_Tshirt": [
            "navy white stripes", "black white stripes"
        ],
        "Long_Sleeve_Tshirt": [
            "white", "charcoal", "navy"
        ]
    },

    "Polos": {
        "Classic_Polo": [
            "navy", "white", "burgundy", "olive"
        ],
        "Knitted_Polo": [
            "charcoal", "camel"
        ]
    },

    "Shirts": {
        "Oxford_Shirt": [
            "white", "light blue", "chambray"
        ],
        "Dress_Shirt": [
            "white", "light blue", "pale pink"
        ],
        "Casual_Check_Shirt": [
            "navy green check", "grey black check"
        ],
        "Linen_Shirt": [
            "white", "beige", "light blue"
        ],
        "Cuban_Collar_Shirt": [
            "cream", "slate blue"
        ]
    },

    "Knitwear": {
        "Crew_Neck_Sweater": [
            "navy", "grey", "camel"
        ],
        "Turtleneck": [
            "black", "charcoal", "olive"
        ],
        "Cardigan": [
            "navy", "brown"
        ]
    },

    # ======================
    # BOTTOMS
    # ======================

    "Bottoms": {
        "Jeans": [
            "deep indigo", "mid blue", "black"
        ],
        "Chinos": [
            "khaki", "navy", "olive", "stone"
        ],
        "Formal_Trousers": [
            "charcoal", "navy"
        ],
        "Pleated_Trousers": [
            "camel", "slate blue"
        ],
        "Cargo_Pants": [
            "olive", "stone"
        ],
        "Joggers": [
            "charcoal", "navy", "black"
        ],
        "Shorts": [
            "khaki", "navy"
        ]
    },

    # ======================
    # OUTERWEAR
    # ======================

    "Outerwear": {
        "Blazer": [
            "navy", "charcoal"
        ],
        "Textured_Blazer": [
            "brown tweed", "olive tweed"
        ],
        "Denim_Jacket": [
            "mid blue"
        ],
        "Bomber_Jacket": [
            "black", "olive"
        ],
        "Overshirt_Shacket": [
            "olive", "grey check"
        ],
        "Leather_Jacket": [
            "black leather", "dark brown leather"
        ],
        "Field_Jacket": [
            "olive", "dark khaki"
        ],
        "Overcoat": [
            "camel", "charcoal"
        ],
        "Peacoat": [
            "navy", "black"
        ],
        "Puffer_Jacket": [
            "black", "deep green"
        ],
        "Hoodie": [
            "charcoal", "olive", "heather grey"
        ]
    },

    # ======================
    # FOOTWEAR
    # ======================

    "Footwear": {
        "White_Sneakers": [
            "white leather"
        ],
        "Minimal_Sneakers": [
            "black", "grey"
        ],
        "Chelsea_Boots": [
            "brown leather", "black leather"
        ],
        "Chukka_Boots": [
            "sand suede", "taupe suede"
        ],
        "Derby_Shoes": [
            "dark brown leather"
        ],
        "Oxford_Shoes": [
            "black leather"
        ],
        "Loafers": [
            "brown leather", "black leather"
        ],
        "Sandals": [
            "brown leather"
        ],
        "Running_Shoes": [
            "black", "white"
        ]
    },

    # ======================
    # ACCESSORIES
    # ======================

    "Accessories": {
        "Watch": [
            "silver steel", "black leather strap", "brown leather strap"
        ],
        "Sunglasses": [
            "black frame", "tortoiseshell"
        ],
        "Belt": [
            "black leather", "brown leather"
        ],
        "Bracelet": [
            "leather", "metal"
        ],
        "Pendant": [
            "silver chain", "gold chain"
        ],
        "Cap": [
            "black", "navy"
        ],
        "Beanie": [
            "charcoal", "olive"
        ],
        "Scarf": [
            "charcoal wool", "navy wool"
        ],
        "Gloves": [
            "black leather", "brown leather"
        ],
        "Bag": [
            "black backpack", "brown leather messenger", "canvas weekender"
        ]
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def is_valid_image(response):
    content_type = response.headers.get("Content-Type", "")
    return "image" in content_type

def download_images():
    with DDGS() as ddgs:
        for category, items in WARDROBE.items():
            for item, colors in items.items():
                for color in colors:

                    query = f"{color} {item.replace('_', ' ')} men fashion studio"
                    save_dir = os.path.join(
                        ROOT_DIR, category, item, color.replace(" ", "_")
                    )
                    os.makedirs(save_dir, exist_ok=True)

                    print(f"\n🔍 Searching: {query}")

                    try:
                        results = ddgs.images(query, max_results=10)
                    except Exception as e:
                        print(f"⚠ Search blocked, skipping query: {e}")
                        time.sleep(REQUEST_DELAY)
                        continue

                    saved = 0

                    for idx, result in enumerate(results, start=1):
                        if saved >= IMAGES_PER_ITEM:
                            break

                        try:
                            url = result.get("image")
                            if not url:
                                continue

                            response = requests.get(url, headers=HEADERS, timeout=10)
                            if not is_valid_image(response):
                                continue

                            img = Image.open(BytesIO(response.content)).convert("RGB")

                            filename = f"{item}_{color.replace(' ', '_')}_{saved+1}.jpg"
                            img.save(os.path.join(save_dir, filename), "JPEG", quality=90)

                            saved += 1
                            print(f"✔ Saved: {filename}")

                        except Exception:
                            continue

                    time.sleep(REQUEST_DELAY)

if __name__ == "__main__":
    os.makedirs(ROOT_DIR, exist_ok=True)
    download_images()
    print("\n🎯 Wardrobe dataset completed safely.")
