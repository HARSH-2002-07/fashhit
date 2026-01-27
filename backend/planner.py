import numpy as np
import colorsys
from typing import List, Dict, Tuple, Optional
from fashion_clip.fashion_clip import FashionCLIP
from store import WardrobeStore
from ontology import OUTFIT_TEMPLATES, Category

# --- CONFIGURATION: COLOR FALLBACKS ---
# If Gemini didn't save a specific HEX code, we use these approximations
# to ensure the math never crashes.
NAME_TO_HEX = {
    "black": "#000000", "white": "#FFFFFF", "grey": "#808080", "gray": "#808080",
    "navy": "#000080", "blue": "#0000FF", "light blue": "#ADD8E6",
    "red": "#FF0000", "maroon": "#800000", "burgundy": "#800020",
    "green": "#008000", "khaki": "#F0E68C", "olive": "#808000",
    "beige": "#F5F5DC", "tan": "#D2B48C", "brown": "#A52A2A",
    "yellow": "#FFFF00", "orange": "#FFA500", "pink": "#FFC0CB",
    "purple": "#800080", "cream": "#FFFDD0"
}

# --- MATH HELPER: COLOR PHYSICS ---
def hex_to_hsv(hex_input: str) -> Tuple[float, float, float]:
    """
    Converts HEX (#FF0000) or Color Name ('Red') to HSV (Hue, Saturation, Value).
    Returns (0.0, 0.0, 0.0) if invalid.
    """
    # 1. Normalize input
    if not hex_input:
        return (0.0, 0.0, 0.0)
    
    hex_clean = hex_input.lower().strip()
    
    # 2. Check if it's a name -> Convert to Hex
    if hex_clean in NAME_TO_HEX:
        hex_clean = NAME_TO_HEX[hex_clean]
    
    # 3. Parse Hex
    hex_clean = hex_clean.lstrip('#')
    if len(hex_clean) != 6:
        return (0.0, 0.0, 0.0) # Fail safe
        
    try:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        # Convert RGB (0-255) to HSV (0.0-1.0)
        return colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    except ValueError:
        return (0.0, 0.0, 0.0)

class NeuroSymbolicEngine:
    """
    Hybrid Brain: Combines Rules (Symbolic) with Vectors (Neural).
    """
    
    @staticmethod
    def get_visual_harmony(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Calculates 'Vibe Match' using Deep Learning Vectors.
        Captures texture, lighting, and complex style nuances.
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0: 
            return 0.0
        
        # Cosine Similarity: (A . B) / (|A| * |B|)
        sim = np.dot(vec_a, vec_b) / (norm_a * norm_b)
        return float(sim)

    @staticmethod
    def get_color_score(color_a: str, color_b: str) -> float:
        """
        Mathematical Color Theory (HSV Distance)
        """
        h1, s1, v1 = hex_to_hsv(color_a)
        h2, s2, v2 = hex_to_hsv(color_b)
        
        # 1. NEUTRALS Check (Low Saturation)
        # If either is Gray/Black/White/Beige, it matches everything.
        # Threshold: Saturation < 15% or Value < 15% (Very dark)
        if s1 < 0.15 or s2 < 0.15 or v1 < 0.15 or v2 < 0.15:
            return 0.3  # Safe match bonus

        # 2. HUE DISTANCE (The Color Wheel)
        diff = abs(h1 - h2)
        if diff > 0.5: 
            diff = 1.0 - diff # Handle wrap-around (0.9 is close to 0.1)
        
        # Analogous (0.0 - 0.15) -> Harmony (e.g. Green + Blue)
        if diff < 0.15: 
            return 0.25      
        
        # Complementary (0.4 - 0.6) -> Contrast (e.g. Blue + Orange)
        if 0.4 < diff < 0.6: 
            return 0.20 
            
        # Clash Zone (e.g. Red + Pink)
        return -0.1

    @staticmethod
    def evaluate_pair(item_a: dict, item_b: dict, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        The Master Equation: Combines 3 types of logic into one score.
        """
        score = 0.5 # Base Probability
        
        # --- A. NEURAL CHECK (30%) ---
        # Do they visually look good together?
        score += NeuroSymbolicEngine.get_visual_harmony(vec_a, vec_b) * 0.3
        
        # --- B. SYMBOLIC CHECK (40%) ---
        # 1. Formality
        f_a = item_a['meta'].get('formality', 'Casual')
        f_b = item_b['meta'].get('formality', 'Casual')
        if f_a != f_b:
            if {f_a, f_b} == {"Formal", "Lounge"}: 
                score -= 0.3 # Hard Veto
            else: 
                score -= 0.1 # Soft Penalty
            
        # 2. Pattern
        p_a = item_a['meta'].get('pattern', 'Solid')
        p_b = item_b['meta'].get('pattern', 'Solid')
        # Avoid Pattern + Pattern
        if p_a != 'Solid' and p_b != 'Solid': 
            score -= 0.25
        
        # --- C. PHYSICS CHECK (30%) ---
        # Color Math
        # Try to get specific HEX, fallback to primary_color name
        c_a = item_a['meta'].get('primary_color_hex', item_a['meta'].get('primary_color', 'black'))
        c_b = item_b['meta'].get('primary_color_hex', item_b['meta'].get('primary_color', 'black'))
        
        score += NeuroSymbolicEngine.get_color_score(str(c_a), str(c_b)) * 0.3
        
        return np.clip(score, 0.0, 1.0)

class ProPlanner:
    def __init__(self, store: WardrobeStore):
        self.store = store
        print("🧠 Loading Neuro-Symbolic Planner...")
        self.fclip = FashionCLIP('fashion-clip')
        self.BEAM_WIDTH = 5

    def plan(self, user_query: str, template_name: str = "basic") -> dict:
        print(f"\n🚀 Neuro-Symbolic Planning: '{user_query}'")
        
        # 1. User Intent Vector
        # We wrap query in list [] because encode_text expects a batch
        query_vec = self.fclip.encode_text([user_query], batch_size=1)[0]
        
        # 2. Identify Structure
        # e.g., [Category.TOP, Category.BOTTOM, Category.FOOTWEAR]
        required_slots = OUTFIT_TEMPLATES.get(template_name, OUTFIT_TEMPLATES["basic"])
        slot_names = [s.value for s in required_slots] # ["Top", "Bottom", "Footwear"]
        
        # 3. Retrieve Candidates (Vector Search)
        # Pre-fetch 15 candidates per slot to give the beam search enough options
        candidates_map = {}
        for slot in required_slots:
            results = self.store.vector_search(query_vec, category_filter=slot, top_k=15)
            candidates_map[slot.value] = results
            if not results:
                print(f"⚠️ Warning: No items found for {slot.value}")
                return {}

        # 4. Beam Search Execution
        # Beam Structure: List of tuples -> (cumulative_score, [list_of_full_item_dicts])
        
        # --- Step A: Initialize Beam with First Slot (e.g., Tops) ---
        first_slot_name = slot_names[0]
        beam = []
        
        for cand in candidates_map[first_slot_name]:
            # Initial score is just relevance to the text query
            beam.append( (cand['score'], [cand['item']]) )
            
        # Sort and Keep Top K
        beam = sorted(beam, key=lambda x: x[0], reverse=True)[:self.BEAM_WIDTH]
        
        # --- Step B: Expand Beam through Remaining Slots ---
        for slot_name in slot_names[1:]: # ["Bottom", "Footwear"]
            next_beam = []
            
            for path_score, path_items in beam:
                last_item = path_items[-1]
                
                # Fetch vector for the last item (safely)
                last_id = last_item['id']
                if last_id not in self.store.vectors: continue
                last_vec = self.store.vectors[last_id]
                
                # Try every candidate in the current slot
                for cand in candidates_map[slot_name]:
                    curr_item = cand['item']
                    curr_id = curr_item['id']
                    if curr_id not in self.store.vectors: continue
                    curr_vec = self.store.vectors[curr_id]
                    
                    # 1. Relevance Score (Match to "Date Night")
                    relevance = cand['score']
                    
                    # 2. Compatibility Score (Match to Shirt)
                    compatibility = NeuroSymbolicEngine.evaluate_pair(
                        last_item, curr_item, last_vec, curr_vec
                    )
                    
                    # 3. Update Path Score (Weighted Moving Average)
                    # We weight History slightly higher to maintain coherence
                    new_score = (path_score * 0.4) + (relevance * 0.3) + (compatibility * 0.3)
                    
                    # Add to potential next beam
                    new_path = path_items + [curr_item]
                    next_beam.append( (new_score, new_path) )
            
            # Prune: Keep only the best K paths overall
            beam = sorted(next_beam, key=lambda x: x[0], reverse=True)[:self.BEAM_WIDTH]

        # 5. Output Result
        if not beam:
            print("❌ Planning failed. No valid combinations.")
            return {}
        
        best_score, best_items = beam[0]
        print(f"✨ Best Outfit (Score: {best_score:.3f})")
        
        outfit_plan = {}
        for i, slot_name in enumerate(slot_names):
            item = best_items[i]
            outfit_plan[slot_name] = item
            
            # Debug Print
            c_name = item['meta'].get('sub_category', 'Item')
            c_color = item['meta'].get('primary_color', 'Unknown')
            print(f"   ✅ {slot_name}: {c_name} ({c_color})")
            
        return outfit_plan

# --- TEST BLOCK ---
if __name__ == "__main__":
    # Ensure this points to your real data directory
    db = WardrobeStore(data_dir="my_wardrobe/data")
    
    # Initialize Planner
    planner = ProPlanner(store=db)
    
    # Run a test
    planner.plan("Smart casual outfit for a coffee date")