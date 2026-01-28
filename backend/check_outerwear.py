"""Check for all outerwear items in detail"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get all outerwear items
result = supabase.table('wardrobe_items').select('*').eq('category', 'outerwear').execute()
items = result.data

print(f"\n🧥 OUTERWEAR ITEMS ({len(items)} total):\n")

for item in items:
    attrs = item.get('attributes', {})
    print(f"ID: {item['id']}")
    print(f"  File ID: {item.get('file_id', 'N/A')}")
    print(f"  Sub-category: {attrs.get('sub_category', 'N/A')}")
    print(f"  Color: {attrs.get('primary_color', 'N/A')}")
    print(f"  Material: {attrs.get('material', 'N/A')}")
    print(f"  Image: {item['clean_image_url'][-50:]}")
    print()
