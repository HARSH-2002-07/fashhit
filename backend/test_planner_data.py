"""Quick diagnostic to check what the planner sees"""
from store import WardrobeStore
from ontology import Category

# Load the store
db = WardrobeStore(data_dir="../my_wardrobe/data")

print("\n📊 INVENTORY BY CATEGORY:")
print(f"Tops: {len(db.get_by_category(Category.TOP))}")
print(f"Bottoms: {len(db.get_by_category(Category.BOTTOM))}")
print(f"Footwear: {len(db.get_by_category(Category.FOOTWEAR))}")
print(f"Outerwear: {len(db.get_by_category(Category.OUTERWEAR))}")

print("\n👕 SAMPLE ITEMS:")
tops = db.get_by_category(Category.TOP)
if tops:
    for t in tops[:3]:
        print(f"- {t['id']}: {t['meta'].get('sub_category')} ({t['meta'].get('primary_color')})")

print("\n🧥 OUTERWEAR ITEMS:")
outerwear = db.get_by_category(Category.OUTERWEAR)
if outerwear:
    for o in outerwear:
        print(f"- {o['id']}: {o['meta'].get('sub_category')} ({o['meta'].get('primary_color')})")
else:
    print("⚠️ NO OUTERWEAR FOUND!")

print("\n🔍 CHECKING EMBEDDINGS:")
print(f"Total items: {len(db.items)}")
print(f"Items with embeddings: {len(db.vectors)}")
missing = [id for id in db.items if id not in db.vectors]
if missing:
    print(f"⚠️ Missing embeddings for: {missing[:5]}")
