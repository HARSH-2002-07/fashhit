import requests
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from typing import List, Dict
from fashion_clip.fashion_clip import FashionCLIP
from store import WardrobeStore
from ontology import OUTFIT_TEMPLATES

# --- 1. VISUALIZER ---
class Visualizer:
    @staticmethod
    def show_outfit(outfit_plan: dict, title: str, recommendation: str = None):
        items = list(outfit_plan.values())
        if not items: return
        
        # Adjust layout for title space
        fig, axes = plt.subplots(1, len(items), figsize=(12, 6))
        if len(items) == 1: axes = [axes]
        
        full_title = title
        if recommendation:
            full_title += f"\n\n SHOPPING TIP: {recommendation}"
            
        fig.suptitle(full_title, fontsize=14)
        
        for ax, (slot, item) in zip(axes, outfit_plan.items()):
            try:
                img_path = item['paths']['clean']
                img = Image.open(img_path)
                ax.imshow(img)
                ax.axis('off')
                meta = item['meta']
                label = f"{slot}\n{meta.get('sub_category')}\n{meta.get('primary_color')}\n({meta.get('fit', 'Reg')})"
                ax.set_title(label, fontsize=9)
            except: 
                ax.axis('off')
        plt.tight_layout()
        plt.show()

# --- 2. LIVE WEATHER ---
class LiveWeather:
    @staticmethod
    def get_weather():
        try:
            loc = requests.get("http://ip-api.com/json/", timeout=2).json()
            lat, lon = loc['lat'], loc['lon']
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            w = requests.get(url, timeout=2).json()
            code = w['current_weather']['weathercode']
            temp = w['current_weather']['temperature']
            cond = "Clear"
            if code in [1, 2, 3]: cond = "Cloudy"
            elif code in [61, 63, 65, 80, 81, 82]: cond = "Rainy"
            elif code in [71, 73, 75, 85, 86]: cond = "Snowy"
            return {"condition": cond, "temp": temp, "city": loc['city']}
        except:
            return {"condition": "Clear", "temp": 25, "city": "Offline"}

# --- 3. SHOPPING ENGINE (NEW) ---
class ShoppingEngine:
    def __init__(self, fclip: FashionCLIP, data_dir: str):
        self.fclip = fclip
        self.essentials = []
        
        # Load Essentials
        path = os.path.join(data_dir, "essentials.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.essentials = json.load(f)
                print(f"🛍️  Virtual Store loaded: {len(self.essentials)} items")
                
            # Pre-compute vectors for virtual items using TEXT description
            # This is the "Zero-Shot" magic
            descriptions = [
                f"{i['meta']['fit']} fit {i['meta']['primary_color']} {i['meta']['sub_category']}" 
                for i in self.essentials
            ]
            self.vectors = self.fclip.encode_text(descriptions, batch_size=len(descriptions))
        else:
            print("⚠️ essentials.json not found. Shopping engine disabled.")

    def find_upgrade(self, current_outfit: dict, current_score: float, query_vec) -> str:
        if not self.essentials: return None
        
        best_upgrade = None
        max_improvement = 0.0
        
        for slot, current_item in current_outfit.items():
            current_cat = current_item['meta']['category']
            current_sub = current_item['meta']['sub_category'].lower()
            current_col = current_item['meta']['primary_color'].lower()
            
            for idx, v_item in enumerate(self.essentials):
                # 1. Category Match
                if v_item['meta']['category'] != current_cat: continue
                
                # --- NEW LOGIC: Redundancy Check ---
                # If you are wearing "Black Boots" and virtual item is "Black Boots", skip.
                v_sub = v_item['meta']['sub_category'].lower()
                v_col = v_item['meta']['primary_color'].lower()
                
                if current_col in v_col and (current_sub in v_sub or v_sub in current_sub):
                    continue # Skip redundant recommendation
                # -----------------------------------

                v_vec = self.vectors[idx]
                relevance = np.dot(query_vec, v_vec)
                improvement = relevance - 0.1 
                
                if improvement > max_improvement and improvement > 0.4:
                    max_improvement = improvement
                    best_upgrade = f"Buy {v_item['meta']['sub_category']} (Increases match score)"
        
        return best_upgrade

# --- 4. LOGIC ENGINES (Existing) ---
class SilhouetteEngine:
    @staticmethod
    def evaluate_proportion(top: dict, bottom: dict) -> float:
        fit_top = top['meta'].get('fit', 'Regular')
        fit_bot = bottom['meta'].get('fit', 'Regular')
        if fit_top in ["Oversized", "Relaxed"] and fit_bot in ["Oversized", "Relaxed"]: return -0.2 
        if fit_top == "Oversized" and fit_bot in ["Slim", "Skinny"]: return 0.2
        if fit_top in ["Slim", "Skinny"] and fit_bot in ["Relaxed", "Oversized"]: return 0.2
        if fit_top == "Slim" and fit_bot == "Slim": return 0.1
        return 0.0

class WeatherEngine:
    SENSITIVE = ["suede", "silk", "satin", "velvet", "canvas", "mesh"]
    @staticmethod
    def is_safe(item: dict, cond: str) -> bool:
        if "rain" not in cond.lower() and "snow" not in cond.lower(): return True
        meta = item['meta']
        name = meta.get('sub_category', '').lower()
        if any(x in name for x in WeatherEngine.SENSITIVE): return False
        if "footwear" in meta.get('category', '').lower() and "white" in meta.get('primary_color', '').lower(): return False
        return True

class ContextBrain:
    @staticmethod
    def detect_template(query: str, weather: dict, fclip: FashionCLIP) -> str:
        q_low = query.lower()
        cond = weather['condition'].lower()
        temp = weather['temp']
        if temp < 15 or "rain" in cond or "snow" in cond: return "layered"
        triggers = ["jacket", "coat", "blazer", "suit", "layer", "bomber"]
        if any(t in q_low for t in triggers): return "layered"
        vecs = fclip.encode_text([query, "cold winter layered outfit", "warm summer outfit"], batch_size=3)
        if np.dot(vecs[0], vecs[1]) > np.dot(vecs[0], vecs[2]): return "layered"
        return "basic"

class NeuroSymbolicEngine:
    @staticmethod
    def evaluate_pair(item_a, item_b, vec_a, vec_b):
        score = 0.5
        score += (np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))) * 0.4
        f_a = item_a['meta'].get('formality', 'Casual')
        f_b = item_b['meta'].get('formality', 'Casual')
        if f_a != f_b:
            if {f_a, f_b} == {"Formal", "Lounge"}: score -= 0.4 
            else: score -= 0.1
        cat_a = item_a['meta'].get('category')
        cat_b = item_b['meta'].get('category')
        if {cat_a, cat_b} == {"Top", "Bottom"}:
            top = item_a if cat_a == "Top" else item_b
            btm = item_b if cat_b == "Bottom" else item_a
            score += SilhouetteEngine.evaluate_proportion(top, btm)
        return score

# --- 5. MASTER PLANNER V7 ---
class ProPlannerV7:
    def __init__(self, store: WardrobeStore):
        self.store = store
        print("🧠 Loading Planner V7 (Shopping Enabled)...")
        self.fclip = FashionCLIP('fashion-clip')
        self.BEAM_WIDTH = 5
        
        # Init Shopping Brain
        self.shopper = ShoppingEngine(self.fclip, store.data_dir)

    def apply_hybrid_ranking(self, candidates: List[dict], query: str) -> List[dict]:
        q = query.lower()
        boosters = ["leather", "denim", "linen", "boots", "sneakers", "hoodie", "bomber"]
        active_boosts = [k for k in boosters if k in q]
        formal_req = "formal" in q or "interview" in q or "wedding" in q
        casual_req = "casual" in q or "chill" in q
        
        for c in candidates:
            meta = c['item']['meta']
            desc = f"{meta.get('sub_category','')} {meta.get('material','')} {meta.get('category','')}".lower()
            formality = meta.get('formality', 'Casual')
            matches = sum(1 for k in active_boosts if k in desc)
            if matches > 0: c['score'] += (matches * 0.5)
            if formal_req and formality == "Casual": c['score'] -= 0.5 
            if casual_req and formality == "Formal": c['score'] -= 0.3
        return sorted(candidates, key=lambda x: x['score'], reverse=True)

    def plan(self, user_query: str, manual_weather: str = None) -> dict:
        weather = LiveWeather.get_weather()
        if manual_weather: weather['condition'] = manual_weather 
        
        print(f"\n🌍 {weather['city']}: {weather['condition']}, {weather['temp']}°C")
        print(f"🚀 Planning for: '{user_query}'")
        
        template_name = ContextBrain.detect_template(user_query, weather, self.fclip)
        required_slots_enums = OUTFIT_TEMPLATES.get(template_name, OUTFIT_TEMPLATES["basic"])
        slot_names = [s.value for s in required_slots_enums]
        
        q_vec = self.fclip.encode_text([user_query], batch_size=1)[0]
        candidates_map = {}
        
        for slot_enum in required_slots_enums:
            raw = self.store.vector_search(q_vec, category_filter=slot_enum, top_k=20)
            ranked = self.apply_hybrid_ranking(raw, user_query)
            valid = [r for r in ranked if WeatherEngine.is_safe(r['item'], weather['condition'])]
            if not valid:
                print(f"⚠️ No valid items for {slot_enum.value}")
                return {}
            candidates_map[slot_enum.value] = valid

        # Beam Search
        first_slot_name = slot_names[0]
        beam = [[(c['score'], [c['item']]) for c in candidates_map[first_slot_name]]]
        beam = sorted(beam[0], reverse=True)[:self.BEAM_WIDTH]
        
        for slot_name in slot_names[1:]:
            next_beam = []
            for score, items in beam:
                last = items[-1]
                l_vec = self.store.vectors[last['id']]
                used_ids = {item['id'] for item in items}  # Track already used items
                for c in candidates_map[slot_name]:
                    curr = c['item']
                    # Skip if this item is already used in the outfit
                    if curr['id'] in used_ids:
                        continue
                    c_vec = self.store.vectors[curr['id']]
                    compatibility = NeuroSymbolicEngine.evaluate_pair(last, curr, l_vec, c_vec)
                    new_score = (score * 0.4) + (c['score'] * 0.3) + (compatibility * 0.3)
                    next_beam.append((new_score, items + [curr]))
            beam = sorted(next_beam, key=lambda x: x[0], reverse=True)[:self.BEAM_WIDTH]

        if not beam: return {}
        best_score, best_items = beam[0]
        outfit = {s: i for s, i in zip(slot_names, best_items)}
        
        print(f"✨ Outfit Found (Score: {best_score:.3f})")
        
        # --- SHOPPING ANALYSIS ---
        upgrade_msg = self.shopper.find_upgrade(outfit, best_score, q_vec)
        if upgrade_msg:
            print(f"💡 SHOPPING INSIGHT: {upgrade_msg}")
        
        # Visualization disabled for API usage (uncomment for standalone testing)
        # Visualizer.show_outfit(outfit, title=f"{user_query} ({weather['condition']})", recommendation=upgrade_msg)
        return outfit

if __name__ == "__main__":
    db = WardrobeStore(data_dir="my_wardrobe copy/data")
    planner = ProPlannerV7(store=db)
    
    # TEST: Ask for a Wedding outfit.
    # Since you only have Jeans, it should trigger a recommendation for "Navy Wool Trousers"
    planner.plan("Blue")