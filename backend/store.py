import os
import json
import numpy as np
from typing import List, Dict, Optional
from ontology import Category

class WardrobeStore:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.items: Dict[str, dict] = {}
        self.vectors: Dict[str, np.ndarray] = {}
        self.refresh()

    def refresh(self):
        """Loads all JSON files from disk into memory."""
        json_dir = os.path.join(self.data_dir, "json")
        self.items = {}
        self.vectors = {}
        
        if not os.path.exists(json_dir):
            print(f"⚠️ No data found in {json_dir}")
            return

        files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
        print(f"📂 Loading {len(files)} items into State Memory...")

        for f in files:
            path = os.path.join(json_dir, f)
            try:
                with open(path, "r") as file:
                    data = json.load(file)
                    item_id = data.get("id")
                    
                    # 1. Store Metadata
                    self.items[item_id] = data
                    
                    # 2. Store Vector (if it exists)
                    if "embedding" in data and data["embedding"]:
                        self.vectors[item_id] = np.array(data["embedding"], dtype=np.float32)
                        
            except Exception as e:
                print(f"❌ Corrupt file {f}: {e}")
        
        print(f"✅ State Loaded: {len(self.items)} physical items, {len(self.vectors)} semantic vectors.")

    def get_by_category(self, category: Category) -> List[dict]:
        """Filter: Get all Tops, or all Shoes"""
        return [
            item for item in self.items.values() 
            if item["meta"].get("category") == category.value
        ]

    def vector_search(self, query_vector: List[float], top_k: int = 5, category_filter: Optional[Category] = None):
        """
        The 'Magic' Search: Finds items mathematically similar to a query vector.
        """
        if not self.vectors:
            return []

        # Convert query to numpy
        query_vec = np.array(query_vector, dtype=np.float32)
        
        # Calculate Cosine Similarity against ALL items
        # (Dot product of normalized vectors)
        scores = []
        for item_id, item_vec in self.vectors.items():
            # Filter by category if requested
            if category_filter:
                item_cat = self.items[item_id]["meta"].get("category")
                if item_cat != category_filter.value:
                    continue

            # Cosine Similarity Formula: (A . B) / (||A|| * ||B||)
            similarity = np.dot(query_vec, item_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(item_vec))
            scores.append((item_id, similarity))

        # Sort by highest score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K items
        results = []
        for item_id, score in scores[:top_k]:
            results.append({
                "item": self.items[item_id],
                "score": float(score)
            })
            
        return results

# --- TEST CODE (Run this file directly to test) ---
if __name__ == "__main__":
    # Initialize the Database
    db = WardrobeStore(data_dir="my_wardrobe/data")
    
    # Test 1: Count Inventory
    print(f"\n📊 Inventory Check:")
    tops = db.get_by_category(Category.TOP)
    bottoms = db.get_by_category(Category.BOTTOM)
    print(f"   - Tops: {len(tops)}")
    print(f"   - Bottoms: {len(bottoms)}")
    
    # Test 2: Print a sample item
    if tops:
        print(f"\n👕 Sample Top: {tops[0]['id']}")
        print(f"   Tags: {tops[0]['meta']}")