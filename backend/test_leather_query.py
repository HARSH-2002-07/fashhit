"""Test the specific query that's not working"""
from planner import ProPlannerV7
from store import WardrobeStore

# Load everything
db = WardrobeStore(data_dir="../my_wardrobe/data")
planner = ProPlannerV7(store=db)

# Test the exact query
print("\n" + "="*60)
print("TESTING: 'leather featuring outfit'")
print("="*60)

outfit = planner.plan("leather featuring outfit")

print("\n📦 RESULT:")
if outfit:
    for slot, item in outfit.items():
        meta = item['meta']
        print(f"{slot}: {meta.get('sub_category')} - {meta.get('primary_color')} ({meta.get('material', 'N/A')})")
else:
    print("❌ No outfit returned!")

print("\n" + "="*60)
print("TESTING: 'casual leather jacket outfit'")
print("="*60)

outfit2 = planner.plan("casual leather jacket outfit")

print("\n📦 RESULT:")
if outfit2:
    for slot, item in outfit2.items():
        meta = item['meta']
        print(f"{slot}: {meta.get('sub_category')} - {meta.get('primary_color')} ({meta.get('material', 'N/A')})")
else:
    print("❌ No outfit returned!")
