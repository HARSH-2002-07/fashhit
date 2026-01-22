import numpy as np
from fashion_clip.fashion_clip import FashionCLIP
from store import WardrobeStore
from ontology import Category, OUTFIT_TEMPLATES

class OutfitPlanner:
    def __init__(self, store: WardrobeStore):
        self.store = store
        print("🧠 Loading Planner Logic...")
        # We need FashionCLIP here to convert text queries ("Date Night") into vectors
        self.fclip = FashionCLIP('fashion-clip')

    def plan(self, user_query: str, template_name: str = "basic") -> dict:
        """
        The Main Brain Function.
        Input: "I need an outfit for a winter coffee date"
        Output: { "top": {item}, "bottom": {item}, ... }
        """
        print(f"\n🤔 Planning outfit for: '{user_query}'")
        
        # 1. UNDERSTAND INTENT (Text -> Vector)
        # We assume the query describes the *vibe* of the outfit
        query_vector = self.fclip.encode_text([user_query], batch_size=1)[0]
        
        # 2. IDENTIFY GOAL (Which slots do we need to fill?)
        required_slots = OUTFIT_TEMPLATES.get(template_name, OUTFIT_TEMPLATES["basic"])
        
        outfit_plan = {}
        
        # 3. EXECUTE SEARCH (Find best candidate for each slot)
        for category in required_slots:
            # Ask the Store: "Find me the best [CATEGORY] that matches [VECTOR]"
            candidates = self.store.vector_search(
                query_vector=query_vector, 
                category_filter=category, 
                top_k=3 # We get top 3 to have backup options
            )
            
            if not candidates:
                print(f"⚠️ Warning: No items found for {category.value}")
                outfit_plan[category.value] = None
                continue
                
            # STRATEGY: Greedy Selection
            # Simply pick the #1 mathematically closest match for now.
            # (Later we can add LLM reasoning here to pick between the top 3)
            best_match = candidates[0]
            outfit_plan[category.value] = best_match["item"]
            
            print(f"   ✅ Selected {category.value}: {best_match['item']['id']} (Score: {best_match['score']:.2f})")

        return outfit_plan

# --- TEST CODE ---
if __name__ == "__main__":
    # 1. Load Memory
    db = WardrobeStore(data_dir="my_wardrobe/data")
    
    # 2. Load Brain
    stylist = OutfitPlanner(store=db)
    
    # 3. Test Scenarios
    scenarios = [
        "Formal office meeting",
        "Casual Sunday morning coffee",
        "Party at a night club"
    ]
    
    for scene in scenarios:
        result = stylist.plan(scene)
        print("-" * 30)