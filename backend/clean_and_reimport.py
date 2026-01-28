"""
Clean database and Cloudinary, then re-import all wardrobe items
WARNING: This will delete ALL wardrobe items and saved outfits (but keep users)
"""

import os
import json
import requests
import hashlib
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')
CLOUDINARY_UPLOAD_PRESET = os.getenv('CLOUDINARY_UPLOAD_PRESET')

# Paths
WARDROBE_DIR = Path("../my_wardrobe/data")
JSON_DIR = WARDROBE_DIR / "json"
IMAGES_DIR = WARDROBE_DIR / "images"

USER_ID = "c1a4da1b-0582-4afa-8cc6-63c6ccc203da"

def delete_from_cloudinary(public_id):
    """Delete an image from Cloudinary with proper signature"""
    try:
        timestamp = int(time.time())
        
        # Create signature
        to_sign = f"public_id={public_id}&timestamp={timestamp}{CLOUDINARY_API_SECRET}"
        signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
        
        url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/destroy"
        data = {
            'public_id': public_id,
            'timestamp': timestamp,
            'api_key': CLOUDINARY_API_KEY,
            'signature': signature
        }
        
        response = requests.post(url, data=data)
        result = response.json()
        
        # Cloudinary returns 'ok' or 'not found' - both are acceptable
        if result.get('result') in ['ok', 'not found']:
            return True
        
        print(f"   ⚠️ Cloudinary delete result: {result}")
        return False
    except Exception as e:
        print(f"   ⚠️ Cloudinary delete failed for {public_id}: {e}")
        return False

def clean_database():
    """Clean all wardrobe items and saved outfits from database and Cloudinary"""
    print("\n🧹 Starting cleanup...")
    print("=" * 50)
    
    # Get all wardrobe items
    try:
        items_result = supabase.table('wardrobe_items').select('*').execute()
        items = items_result.data
        print(f"📦 Found {len(items)} wardrobe items to delete")
    except Exception as e:
        print(f"⚠️ Error fetching items: {e}")
        items = []
    
    # Delete images from Cloudinary
    cloudinary_deleted = 0
    cloudinary_failed = 0
    if items:
        print("\n☁️ Deleting images from Cloudinary...")
        for item in items:
            raw_id = item.get('raw_cloudinary_id')
            clean_id = item.get('clean_cloudinary_id')
            
            if raw_id:
                print(f"   Deleting: {raw_id}")
                if delete_from_cloudinary(raw_id):
                    cloudinary_deleted += 1
                else:
                    cloudinary_failed += 1
                    
            if clean_id and clean_id != raw_id:  # Don't delete same ID twice
                print(f"   Deleting: {clean_id}")
                if delete_from_cloudinary(clean_id):
                    cloudinary_deleted += 1
                else:
                    cloudinary_failed += 1
                    
        print(f"   ✅ Deleted {cloudinary_deleted} images from Cloudinary")
        if cloudinary_failed > 0:
            print(f"   ⚠️ Failed to delete {cloudinary_failed} images")
    
    # Delete wardrobe items from Supabase
    try:
        result = supabase.table('wardrobe_items').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"   ✅ Deleted all wardrobe items from Supabase")
    except Exception as e:
        print(f"   ⚠️ Error deleting wardrobe items: {e}")
    
    # Delete saved outfits from Supabase
    try:
        result = supabase.table('saved_outfits').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"   ✅ Deleted all saved outfits from Supabase")
    except Exception as e:
        print(f"   ⚠️ Error deleting saved outfits: {e}")
    
    print("\n✅ Cleanup complete!")
    return True

def upload_to_cloudinary(image_path, folder):
    """Upload image to Cloudinary and return the URL"""
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
    
    with open(image_path, 'rb') as image_file:
        files = {'file': image_file}
        data = {
            'upload_preset': CLOUDINARY_UPLOAD_PRESET,
            'folder': folder
        }
        
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'url': result['secure_url'],
                'public_id': result['public_id']
            }
        else:
            raise Exception(f"Cloudinary upload failed: {response.text}")

def migrate_item(json_path):
    """Migrate a single wardrobe item to database"""
    try:
        # Load JSON metadata
        with open(json_path, 'r', encoding='utf-8') as f:
            item_data = json.load(f)
        
        meta = item_data.get('meta', {})
        embedding = item_data.get('embedding', [])
        
        # Find corresponding image file
        image_filename = json_path.stem + '_clean.png'
        clean_image_path = IMAGES_DIR / image_filename
        
        if not clean_image_path.exists():
            image_filename = json_path.stem + '.png'
            clean_image_path = IMAGES_DIR / image_filename
        
        if not clean_image_path.exists():
            print(f"   ⚠️ Image not found: {json_path.stem}")
            return False
        
        # Determine category
        category = meta.get('category', '').lower()
        if category == 'top':
            category = 'tops'
        elif category == 'bottom':
            category = 'bottoms'
        elif category == 'footwear':
            category = 'shoes'
        elif category == 'outerwear':
            category = 'outerwear'  # Keep outerwear as separate category
        elif not category:
            category = 'tops'
        
        # Upload to Cloudinary
        clean_cloudinary = upload_to_cloudinary(clean_image_path, 'wardrobe/clean')
        raw_cloudinary = clean_cloudinary  # Use clean as raw fallback
        
        # Prepare database entry
        db_entry = {
            'user_id': USER_ID,
            'raw_image_url': raw_cloudinary['url'],
            'raw_cloudinary_id': raw_cloudinary['public_id'],
            'clean_image_url': clean_cloudinary['url'],
            'clean_cloudinary_id': clean_cloudinary['public_id'],
            'category': category,
            'file_name': clean_image_path.name,
            'attributes': meta,
            'embedding': embedding if embedding else None
        }
        
        # Insert into Supabase
        result = supabase.table('wardrobe_items').insert(db_entry).execute()
        
        sub_cat = meta.get('sub_category', 'Unknown')
        has_embedding = '✓' if embedding else '✗'
        print(f"   ✅ {sub_cat} ({category}) [Embedding: {has_embedding}]")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {json_path.name} - {e}")
        return False

def import_all_items():
    """Import all wardrobe items from local files"""
    print("\n📥 Starting import...")
    print("=" * 50)
    
    # Get all JSON files
    json_files = sorted(JSON_DIR.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ No JSON files found in {JSON_DIR}")
        return
    
    print(f"📦 Found {len(json_files)} items to import\n")
    
    success_count = 0
    fail_count = 0
    
    for json_path in json_files:
        if migrate_item(json_path):
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 50)
    print("📊 Import Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📦 Total: {len(json_files)}")

def main():
    print("🚀 Database Cleanup & Re-import Script")
    print("=" * 50)
    print("⚠️  WARNING: This will DELETE all wardrobe items and saved outfits!")
    print("⚠️  User data will NOT be deleted")
    print("=" * 50)
    
    response = input("\nAre you sure you want to continue? (yes/no): ").lower()
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled")
        return
    
    # Step 1: Clean database and Cloudinary
    if not clean_database():
        print("❌ Cleanup failed, aborting import")
        return
    
    # Step 2: Import all items
    import_all_items()
    
    print("\n🎉 Complete! Database cleaned and all items re-imported!")

if __name__ == "__main__":
    main()
