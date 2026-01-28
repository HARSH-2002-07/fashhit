"""Check what categories items are stored as in Supabase"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get all wardrobe items
result = supabase.table('wardrobe_items').select('*').execute()
items = result.data

print(f"\n📊 Found {len(items)} items in database\n")

# Check for leather jacket specifically
leather_items = [item for item in items if 'leather' in item['id'].lower() or 'leather' in str(item.get('attributes', {})).lower()]

print("🧥 LEATHER ITEMS:")
for item in leather_items:
    attrs = item.get('attributes', {})
    print(f"\nID: {item['id']}")
    print(f"  Database Category: {item['category']}")
    print(f"  Attributes Category: {attrs.get('category', 'N/A')}")
    print(f"  Sub-category: {attrs.get('sub_category', 'N/A')}")
    print(f"  Has embedding: {len(item.get('embedding', [])) > 0}")

# Count by category
from collections import Counter
category_counts = Counter(item['category'] for item in items)
print(f"\n📈 CATEGORY DISTRIBUTION:")
for cat, count in category_counts.items():
    print(f"  {cat}: {count}")
