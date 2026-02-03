import requests
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from typing import List, Dict
from fashion_clip.fashion_clip import FashionCLIP
from store import WardrobeStore
from ontology import OUTFIT_TEMPLATES, Category, StyleIntent
from intent_formality import formality_bias
from intent_color_mood import color_mood_bias
import math
from statistics import mean
from consistency import compute_outfit_consistency
from supabase import create_client
from dotenv import load_dotenv
import random

load_dotenv()

DEBUG_REASONING = True

COLOR_GROUPS = {
    "neutral": {"black", "white", "grey", "gray", "navy", "beige", "cream", "tan", "brown"},
    "warm": {"red", "orange", "yellow", "maroon", "pink"},
    "cool": {"blue", "green", "olive", "purple"}
}

CONFIDENCE_THRESHOLDS = {
    "minimum": 0.55,
    "good": 0.70,
    "excellent": 0.85
}

CONFIDENCE_WEIGHTS = {
    "silhouette": 0.25,
    "layering": 0.15,
    "visual": 0.20,
    "color": 0.15,
    "formality": 0.10,
    "weather": 0.05,
    "versatility": 0.10
}

SLOT_WEIGHTS = {
    "Top": 1.2,
    "Footwear": 1.15,
    "Outerwear": 1.1,
    "Bottom": 1.0,
    "Accessory": 0.7,
}

INTENT_TOPK = {
    StyleIntent.FORMAL_EVENT: 8,
    StyleIntent.SMART_CASUAL: 10,
    StyleIntent.CASUAL_DAY: 12,
    StyleIntent.STREET: 14,
    StyleIntent.LAYERED_COLD: 12,
}

INTENT_RULES = {
    StyleIntent.CASUAL_DAY: {
        "allowed_formalities": {"Casual", "Lounge"},
        "penalty_formal": 0.4,
        "bonus_match": 0.15,
    },
    StyleIntent.SMART_CASUAL: {
        "allowed_formalities": {"Casual", "Smart Casual"},
        "penalty_formal": 0.25,
        "bonus_match": 0.20,
    },
    StyleIntent.FORMAL_EVENT: {
        "allowed_formalities": {"Formal", "Smart Casual"},
        "penalty_formal": 0.5,
        "bonus_match": 0.30,
    },
    StyleIntent.STREET: {
        "allowed_formalities": {"Casual"},
        "penalty_formal": 0.35,
        "bonus_match": 0.20,
    },
    StyleIntent.LAYERED_COLD: {
        "allowed_formalities": {"Casual", "Smart Casual"},
        "penalty_formal": 0.20,
        "bonus_match": 0.15,
    },
    StyleIntent.LOUNGE: {
        "allowed_formalities": {"Lounge", "Casual"},
        "penalty_formal": 0.6,
        "bonus_match": 0.10,
    },
}


def intent_consistency_bonus(outfit: dict, intent: StyleIntent) -> float:
    rules = INTENT_RULES.get(intent)
    if not rules:
        return 0.0

    allowed = rules["allowed_formalities"]
    bonus = rules["bonus_match"]
    penalty = rules["penalty_formal"]

    score = 0.0

    for item in outfit.values():
        f = item["meta"].get("formality", "Casual")
        if f in allowed:
            score += bonus
        else:
            score -= penalty

    return score / max(len(outfit), 1)



def formality_score(outfit: dict) -> float:
    formalities = [
        item['meta'].get('formality', 'Casual')
        for item in outfit.values()
    ]
    return 1.0 if len(set(formalities)) == 1 else 0.5

def visual_harmony(outfit: dict, vectors: dict) -> float:
    vecs = [vectors[item['id']] for item in outfit.values()]
    if len(vecs) <= 1:
        return 1.0

    centroid = np.mean(vecs, axis=0)
    sims = []

    for v in vecs:
        sim = np.dot(v, centroid) / (np.linalg.norm(v) * np.linalg.norm(centroid))
        sims.append(sim)

    return float(np.clip(np.mean(sims), 0.0, 1.0))



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
            # Clean title without emojis to prevent Matplotlib warnings
            full_title += f"\n\n[SHOPPING TIP]: {recommendation}"
            
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

# --- 3. SHOPPING ENGINE ---

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
            # FIX: Use .get() to handle missing keys safely (e.g., Belts don't have 'fit')
            descriptions = []
            for i in self.essentials:
                meta = i.get('meta', {})
                desc = (
                    f"{meta.get('fit', '')} "
                    f"{meta.get('primary_color', '')} "
                    f"{meta.get('sub_category', '')} "
                    f"{meta.get('material', '')}"
                ).strip()
                descriptions.append(desc)

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
                
                # 2. Redundancy Check (Don't recommend what user already wears)
                v_sub = v_item['meta']['sub_category'].lower()
                v_col = v_item['meta']['primary_color'].lower()
                
                # Loose matching to catch things like "Blue Jeans" vs "Navy Jeans"
                if (current_col in v_col or v_col in current_col) and \
                   (current_sub in v_sub or v_sub in current_sub):
                    continue 

                # 3. Score Improvement Check
                v_vec = self.vectors[idx]
                relevance = np.dot(query_vec, v_vec)
                improvement = relevance - 0.1 # Bias for "Real" items
                
                if improvement > max_improvement and improvement > 0.4:
                    max_improvement = improvement
                    best_upgrade = f"Buy {v_item['meta']['sub_category']} (Increases match score)"
        
        return best_upgrade
# --- 4. LOGIC ENGINES ---

class SilhouetteEngine:
    @staticmethod
    def evaluate_proportion(top: dict, bottom: dict) -> float:
        v_top = top['meta'].get('silhouette_volume', 'Regular')
        v_bot = bottom['meta'].get('silhouette_volume', 'Regular')

        if v_top == "Wide" and v_bot == "Wide":
            return -0.3
        if v_top != v_bot:
            return 0.2
        return 0.1

class LayerEngine:
    @staticmethod
    def evaluate_layers(outfit: dict, template_name: str) -> float:
        if template_name != "layered":
            return 0.0

        roles = [i['meta'].get('layer_role') for i in outfit.values()]

        if "Outer" not in roles:
            return -0.5
        if roles.count("Outer") > 1:
            return -0.2

        return 0.2

# In planner.py

class PhysicsEngine:
    """Ensures layers fit physically (no bulk under slim fit)."""
    
    # Items that are physically thick/bulky
    HIGH_BULK_ITEMS = [
        "Shawl Cardigan", "Chunky", "Cable Knit", "Heavy Hoodie", 
        "Puffer", "Oversized Hoodie", "Thick Sweater"
    ]
    
    # Outerwear that is fitted/structured (cannot take bulk)
    LOW_CAPACITY_OUTER = [
        "Blazer", "Suit Jacket", "Denim Jacket", 
        "Slim", "Tailored", "Biker Jacket"
    ]

    @staticmethod
    def check_layering_physics(inner_item: dict, outer_item: dict) -> float:
        """Returns a penalty if layering is physically impossible."""
        
        inner_sub = inner_item['meta'].get('sub_category', '')
        inner_fit = inner_item['meta'].get('fit', '')
        
        outer_sub = outer_item['meta'].get('sub_category', '')
        outer_fit = outer_item['meta'].get('fit', '')

        # Check 1: Bulk under Structure
        # Is the inner item bulky?
        is_bulky = any(x in inner_sub for x in PhysicsEngine.HIGH_BULK_ITEMS) or \
                   inner_fit in ["Oversized", "Loose"]
        
        # Is the outer item low capacity?
        is_tight = any(x in outer_sub for x in PhysicsEngine.LOW_CAPACITY_OUTER) or \
                   outer_fit in ["Slim", "Skinny", "Tailored"]

        if is_bulky and is_tight:
            return -0.5  # Heavy Penalty (Uncomfortable)

        # Check 2: Hoodie under Blazer (Stylistic/Physical clash)
        if "Hoodie" in inner_sub and "Blazer" in outer_sub:
            return -0.3

        return 0.0

class AccessoryEngine:
    """Enforces Accessory Rules (e.g., Leather Matching)"""
    @staticmethod
    def evaluate_accessory(accessory: dict, shoes: dict, outfit_formality: str) -> float:
        acc_meta = accessory['meta']
        shoe_meta = shoes['meta']
        score = 0.0
        
        acc_sub = acc_meta.get('sub_category', '').lower()
        shoe_mat = shoe_meta.get('material', '').lower()
        
        # Rule 1: Leather Matching (Belt must match Shoe color)
        if "belt" in acc_sub:
            shoe_color = shoe_meta.get('primary_color', '').lower()
            belt_color = acc_meta.get('primary_color', '').lower()
            
            # Strict for formal/leather
            if "leather" in shoe_mat or "formal" in outfit_formality.lower():
                if shoe_color == belt_color: score += 0.3
                elif shoe_color in ["black", "brown"] and belt_color != shoe_color: score -= 0.5
            else:
                if shoe_color == belt_color: score += 0.1

        # Rule 2: Formality
        if outfit_formality == "Formal" and acc_meta.get('formality') == "Casual":
            score -= 0.4
            
        return score

class WeatherEngine:
    SENSITIVE = ["suede", "silk", "satin", "velvet", "canvas", "mesh"]

    @staticmethod
    def is_appropriate_temp(item: dict, temp: float) -> bool:
        meta = item['meta']
        sub = meta.get('sub_category', '').lower()
        
        # 1. HEAT STROKE PREVENTION (The Fix)
        # If it's warmer than 15°C (59°F), ban heavy winter gear.
        if temp > 15:
            HEAVY_WINTER_ITEMS = [
                'glove', 'scarf', 'beanie', 'puffer', 
                'heavy coat', 'overcoat', 'parka', 'wool'
            ]
            if any(x in sub for x in HEAVY_WINTER_ITEMS):
                return False
            
        # 2. HYPOTHERMIA PREVENTION
        # If it's colder than 10°C (50°F), ban summer gear.
        if temp < 10:
            SUMMER_ITEMS = ['shorts', 'sandal', 'linen', 'tank']
            if any(x in sub for x in SUMMER_ITEMS):
                return False
                
        # Rule: No exposed skin below 10°C
        if temp < 10:
            if any(x in sub for x in ['shorts', 'sandal', 'linen']):
                return False
                
        return True
    
    @staticmethod
    def is_safe(item: dict, cond: str, temp: float = 20) -> bool:
        if "rain" not in cond.lower() and "snow" not in cond.lower(): return True
        meta = item['meta']
        name = meta.get('sub_category', '').lower()

        if "rain" in cond.lower():
            if any(x in name for x in ["sandal", "slide", "flip", "espadrille"]):
                return False

        if any(x in name for x in WeatherEngine.SENSITIVE): return False
        if "footwear" in meta.get('category', '').lower() and "white" in meta.get('primary_color', '').lower(): return False
        if not WeatherEngine.is_appropriate_temp(item, temp):
            return False
        return True
    

class ContextBrain:
    @staticmethod
    def detect_template(query: str, weather: dict, fclip: FashionCLIP) -> str:
        q_low = query.lower()
        cond = weather['condition'].lower()
        temp = weather['temp']
        
        # Weather Triggers
        if temp < 15 or "rain" in cond or "snow" in cond: return "layered"

        # if any(t in q_low for t in triggers): return "layered"
        
        # Semantic Check
        vecs = fclip.encode_text([query, "cold winter layered outfit", "warm summer outfit"], batch_size=3)
        if np.dot(vecs[0], vecs[1]) > np.dot(vecs[0], vecs[2]): return "layered"
        
        return "basic"

class NeuroSymbolicEngine:
    @staticmethod
    def evaluate_pair(item_a, item_b, vec_a, vec_b):
        score = 0.5
        
        # A. Visual Harmony
        score += (np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))) * 0.4
        
        # B. Formality Check
        f_a = item_a['meta'].get('formality', 'Casual')
        f_b = item_b['meta'].get('formality', 'Casual')
        if f_a != f_b:
            if {f_a, f_b} == {"Formal", "Lounge"}: score -= 0.4 
            else: score -= 0.1
            
        # C. Category-Specific Logic
        cat_a = item_a['meta'].get('category')
        cat_b = item_b['meta'].get('category')

        # --- NEW: PHYSICS CHECK (Layering) ---
        # Detect which is Inner (Top) and which is Outer (Outerwear)
        if {cat_a, cat_b} == {"Top", "Outerwear"}:
            inner = item_a if cat_a == "Top" else item_b
            outer = item_b if cat_b == "Outerwear" else item_a
            
            # Apply Physics Penalty
            physics_score = PhysicsEngine.check_layering_physics(inner, outer)
            score += physics_score
        # -------------------------------------

        # Silhouette is evaluated at outfit-level, not pair-level
            
        # 2. Accessories (Shoes vs Accessory)
        if {cat_a, cat_b} == {"Footwear", "Accessory"}:
            shoe = item_a if cat_a == "Footwear" else item_b
            acc = item_b if cat_b == "Accessory" else item_a
            formality = shoe['meta'].get('formality', 'Casual')
            score += AccessoryEngine.evaluate_accessory(acc, shoe, formality)
            
        return score

class ColorHarmonyEngine:
    @staticmethod
    def _group(color: str) -> str:
        c = color.lower()
        for group, values in COLOR_GROUPS.items():
            if c in values:
                return group
        return "unknown"

    @staticmethod
    def evaluate(outfit: dict) -> float:
        colors = [
            item['meta'].get('primary_color', '').lower()
            for item in outfit.values()
            if item['meta'].get('primary_color')
        ]

        if len(colors) <= 1:
            return 1.0  # Single-color outfits are safe

        groups = [ColorHarmonyEngine._group(c) for c in colors]

        # Rule 1: All same color (monochrome)
        if len(set(colors)) == 1:
            return 1.0

        # Rule 2: Neutral dominance
        neutral_count = groups.count("neutral")
        if neutral_count >= len(groups) - 1:
            return 0.9

        # Rule 3: Mixed warm & cool without neutral
        if "warm" in groups and "cool" in groups and "neutral" not in groups:
            return 0.4

        # Rule 4: Too many non-neutral colors
        loud_colors = [g for g in groups if g in {"warm", "cool"}]
        if len(loud_colors) >= 3:
            return 0.3

        return 0.7

class ExplanationEngine:
    @staticmethod
    def explain(outfit: dict, confidence: dict, template_name: str, weather: dict) -> List[str]:
        reasons = []
        breakdown = confidence["breakdown"]

        # 1. Balance & Fit (Silhouette)
        if breakdown["silhouette"] >= 0.8:
            reasons.append(
                "The overall fit feels balanced — nothing looks too tight or too loose."
            )

        # 2. Layering
        if template_name == "layered" and breakdown["layering"] >= 0.7:
            reasons.append(
                "The layers work well together and add structure without feeling heavy."
            )

        # 3. Color Simplicity
        if breakdown["color"] >= 0.85:
            reasons.append(
                "The colors are simple and easy on the eyes, making the outfit look clean and put together."
            )
        elif breakdown["color"] >= 0.7:
            reasons.append(
                "The color combination feels safe and well-matched for everyday wear."
            )

        # 4. Visual Cohesion
        if breakdown["visual"] >= 0.75:
            reasons.append(
                "All the pieces feel like they belong together, rather than looking randomly picked."
            )

        # 5. Formality Match
        if breakdown["formality"] == 1.0:
            reasons.append(
                "Everything matches the same vibe, so the outfit doesn’t feel confused or mixed."
            )

        # 6. Weather Appropriateness
        if breakdown["weather"] == 1.0:
            reasons.append(
                f"This outfit makes sense for {weather['condition'].lower()} weather and won’t feel uncomfortable."
            )

        # 7. Versatility
        if breakdown["versatility"] >= 0.35:
            reasons.append(
                "Most pieces are versatile, so you can easily reuse them with other outfits."
            )

        # Keep it human: max 4 reasons
        return reasons[:4]


def apply_outfit_rules(outfit: dict, template_name: str) -> float:
    
    score = 0.0

    # Silhouette
    top = outfit.get("Top")
    bottom = outfit.get("Bottom")
    if top and bottom:
        score += SilhouetteEngine.evaluate_proportion(top, bottom)

    # Layering
    score += LayerEngine.evaluate_layers(outfit, template_name)

    # Versatility bias
    for item in outfit.values():
        score += item['meta'].get('pairing_bias', 0.0)

    if template_name == "layered":
        score += 0.1


    return score

def explain_outfit(outfit: dict):
    reasons = []

    for item in outfit.values():
        if item['meta'].get('pairing_bias', 0) > 0.3:
            reasons.append(f"{item['meta']['sub_category']} is highly versatile")

    roles = [
    i['meta'].get('layer_role')
    for i in outfit.values()
    if i['meta'].get('layer_role') not in [None, "None"]
]

    if "Outer" in roles:
        reasons.append("Proper layering achieved")

    return reasons

def compute_confidence(outfit: dict, template_name: str, weather: dict, vectors: dict) -> dict:
    breakdown = {}

    # 1. Silhouette
    top = outfit.get("Top")
    bottom = outfit.get("Bottom")
    breakdown["silhouette"] = (
        1.0 if not top or not bottom
        else max(SilhouetteEngine.evaluate_proportion(top, bottom), 0.0)
    )

    # 2. Layering
    breakdown["layering"] = max(
        LayerEngine.evaluate_layers(outfit, template_name), 0.0
    )

    # 3. Visual Harmony
    breakdown["visual"] = visual_harmony(outfit, vectors)

    # 4. Color Harmony
    breakdown["color"] = ColorHarmonyEngine.evaluate(outfit)

    # 5. Formality
    breakdown["formality"] = formality_score(outfit)

    # 6. Weather Safety
    breakdown["weather"] = (
        1.0 if all(
            WeatherEngine.is_safe(i, weather['condition'])
            for i in outfit.values()
        ) else 0.5
    )

    # 7. Versatility
    breakdown["versatility"] = np.mean([
        item['meta'].get('pairing_bias', 0.0)
        for item in outfit.values()
    ])

    # Final Weighted Sum
    confidence = sum(
        breakdown[k] * CONFIDENCE_WEIGHTS[k]
        for k in CONFIDENCE_WEIGHTS
    )

    return {
        "score": round(confidence, 3),
        "breakdown": breakdown
    }


# --- 5. MASTER PLANNER V7 ---
class ProPlannerV7:
    def __init__(self, store: WardrobeStore, supabase_client=None):
        self.store = store
        print("🧠 Loading Planner V7 (Shopping & Accessories Enabled)...")
        self.fclip = FashionCLIP('fashion-clip')
        self.BEAM_WIDTH = 5
        
        # Init Shopping Brain
        self.shopper = ShoppingEngine(self.fclip, store.data_dir)
        
        # Use provided Supabase client or try to create one
        if supabase_client:
            self.supabase = supabase_client
            print("✅ Supabase client connected for feedback learning")
        else:
            # Fallback: try to create from environment
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            self.supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
            if self.supabase:
                print("✅ Supabase client created from environment")
            else:
                print("⚠️  No Supabase client - feedback learning disabled")
        
        self.user_feedback_cache = {}  # Cache feedback to avoid repeated queries

    def get_user_feedback(self, user_id: str) -> Dict[str, any]:
        """Fetch and analyze user's feedback history for personalized recommendations."""
        if not user_id:
            print("⚠️  No user_id provided for feedback lookup")
            return {'item_pairs': {}, 'liked_items': set(), 'disliked_items': set()}
        
        if not self.supabase:
            print("⚠️  Supabase client not available - cannot fetch feedback")
            return {'item_pairs': {}, 'liked_items': set(), 'disliked_items': set()}
        
        # Check cache first
        if user_id in self.user_feedback_cache:
            cached = self.user_feedback_cache[user_id]
            print(f"💾 Using cached feedback: {len(cached['disliked_items'])} dislikes, {len(cached['liked_items'])} likes")
            return cached
        
        try:
            # Fetch user's feedback from database
            print(f"🔍 Querying feedback for user: {user_id[:8]}...")
            result = self.supabase.table('outfit_feedback').select('*').eq('user_id', user_id).execute()
            
            print(f"📊 Query returned {len(result.data) if result.data else 0} feedback records")
            
            if not result.data:
                return {'item_pairs': {}, 'liked_items': set(), 'disliked_items': set()}
            
            # Analyze feedback patterns
            item_pairs = {}  # {(item1_id, item2_id): score}
            liked_items = set()
            disliked_items = set()
            
            for feedback in result.data:
                rating = feedback.get('rating')  # 'like' or 'dislike'
                outfit_items = feedback.get('outfit_items', {})
                
                # Extract item IDs from outfit
                item_ids = [str(item.get('id')) for item in outfit_items.values() if item and item.get('id')]
                
                # Track individual item preferences
                if rating == 'like':
                    liked_items.update(item_ids)
                elif rating == 'dislike':
                    disliked_items.update(item_ids)
                
                # Track item pair preferences (combinations)
                for i, id1 in enumerate(item_ids):
                    for id2 in item_ids[i+1:]:
                        pair = tuple(sorted([id1, id2]))
                        if pair not in item_pairs:
                            item_pairs[pair] = 0
                        
                        # Positive for likes, negative for dislikes
                        item_pairs[pair] += 1 if rating == 'like' else -1
            
            feedback_data = {
                'item_pairs': item_pairs,
                'liked_items': liked_items,
                'disliked_items': disliked_items
            }
            
            # Cache the result
            self.user_feedback_cache[user_id] = feedback_data
            
            # Debug output
            print(f"\n🔍 FEEDBACK ANALYSIS for user {user_id[:8]}...")
            print(f"   📚 Liked items: {len(liked_items)}")
            print(f"   🚫 Disliked items: {len(disliked_items)}")
            print(f"   🔗 Item pairs tracked: {len(item_pairs)}")
            
            if disliked_items:
                print(f"   ⚠️  Will avoid: {list(disliked_items)[:5]}...")
            if liked_items:
                print(f"   ✨ Will prefer: {list(liked_items)[:5]}...")
            
            return feedback_data
            
        except Exception as e:
            print(f"⚠️ Error fetching user feedback: {str(e)}")
            return {'item_pairs': {}, 'liked_items': set(), 'disliked_items': set()}
    
    def apply_hybrid_ranking(self, candidates: List[dict], query: str) -> List[dict]:
        q = query.lower()
        boosters = ["leather", "denim", "linen", "boots", "sneakers", "hoodie", "bomber", "belt", "watch"]
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

    def plan(self, user_query: str, manual_weather: str = None, user_id: str = None) -> dict:
        
        # Get user's feedback history for personalization
        user_feedback = self.get_user_feedback(user_id) if user_id else None
        
        if user_feedback and (user_feedback['disliked_items'] or user_feedback['liked_items']):
            print(f"\n🎯 FEEDBACK ACTIVE: {len(user_feedback['disliked_items'])} dislikes, {len(user_feedback['liked_items'])} likes")
        else:
            print(f"\n🎯 No user feedback found (user_id: {user_id})")
        
        weather = LiveWeather.get_weather()
        if manual_weather: weather['condition'] = manual_weather 
        
        # In planner.plan()
        query_lower = user_query.lower()
        if "rain" in query_lower or "storm" in query_lower:
            weather['condition'] = "Rainy"
        elif "hot" in query_lower or "summer" in query_lower:
            weather['temp'] = 30 # Override temp context
        
        print(f"\n🌍 {weather['city']}: {weather['condition']}, {weather['temp']}°C")
        print(f"🚀 Planning for: '{user_query}'")
        
        template_name = ContextBrain.detect_template(user_query, weather, self.fclip)
        template = OUTFIT_TEMPLATES.get(template_name, OUTFIT_TEMPLATES["basic"])

        slot_rules = template["slots"]
        slot_names = [slot["category"].value for slot in slot_rules]

        print("🧩 Template:", template_name)
        print("🧩 Slots:", [slot["category"].value for slot in slot_rules])

        q_vec = self.fclip.encode_text([user_query], batch_size=1)[0]
        candidates_map = {}        
        # q_vec = self.fclip.encode_text([user_query], batch_size=1)[0]
        # candidates_map = {}

        INTENT_TOPK = {
    StyleIntent.FORMAL_EVENT: 8,
    StyleIntent.SMART_CASUAL: 10,
    StyleIntent.CASUAL_DAY: 12,
    StyleIntent.STREET: 14,
    StyleIntent.LAYERED_COLD: 12,
}

        # 1. Retrieval
        for slot in slot_rules:
            category = slot["category"]
            required = slot.get("required", True)
            slot_name = category.value
            top_k = INTENT_TOPK.get(template["intent"], 12)
            raw = self.store.vector_search(q_vec, category_filter=slot_name, top_k=top_k)

            intent = template["intent"]

            ranked = []
            for r in raw:
                fb = formality_bias(r["item"], intent)
                cb = color_mood_bias(r["item"], intent)
                jitter = random.uniform(0.85, 1.15) 
                r["score"] *= (fb * cb * jitter)
                ranked.append(r)

            ranked.sort(key=lambda x: x["score"], reverse=True)

            valid = [r for r in ranked if WeatherEngine.is_safe(r['item'], weather['condition'])]
            
            if not valid:
                # Accessories might not be in user wardrobe yet, don't fail, just warn
                if category == Category.ACCESSORY and not required:
                    print("⚠️ No Accessories found in wardrobe (Skipping slot)")
                    continue
                else:
                    print(f"⚠️ No valid items for {slot_name} slot. Aborting outfit plan.")
                    return {}
            
            candidates_map[slot_name] = valid

        # Filter slot names to only those we found items for
        valid_slot_names = [s for s in slot_names if s in candidates_map]

        # 2. Beam Search
        first_slot = valid_slot_names[0]
        beam = [[(c['score'], [c['item']]) for c in candidates_map[first_slot]]]
        beam = sorted(beam[0], reverse=True)[:self.BEAM_WIDTH]
        
        for slot_name in valid_slot_names[1:]:
            next_beam = []
            for score, items in beam:
                last = items[-1]
                l_vec = self.store.vectors[last['id']]
                
                for c in candidates_map[slot_name]:
                    curr = c['item']
                    c_vec = self.store.vectors[curr['id']]
                    curr_id = str(curr.get('id', curr['meta'].get('id', '')))
                    
                    # DEBUG: Print first few items to see ID structure
                    if slot_name == valid_slot_names[1] and score == beam[0][0]:
                        print(f"🔍 DEBUG Item ID check: curr['id']={curr.get('id', 'N/A')}, curr['meta']['id']={curr['meta'].get('id', 'N/A')}")
                        if user_feedback:
                            print(f"🔍 DEBUG: Is {curr_id} in disliked_items? {curr_id in user_feedback['disliked_items']}")
                            print(f"🔍 DEBUG: Sample disliked IDs: {list(user_feedback['disliked_items'])[:3]}")

                    # STRONG FILTER: Skip heavily disliked items early
                    if user_feedback and curr_id in user_feedback['disliked_items']:
                        print(f"🚫 SKIPPING disliked item: {curr['meta'].get('sub_category', 'Unknown')} (ID: {curr_id})")
                        continue

                    if not WeatherEngine.is_safe(curr, weather["condition"]):
                        continue
                    
                    used = {i["meta"]["sub_category"] for i in items}

                    compatibility = NeuroSymbolicEngine.evaluate_pair(
                        last, curr, l_vec, c_vec
                    )

                    if curr["meta"]["sub_category"] in used:
                        compatibility -= 0.2

                    # Weighted Score
                    slot_weight = SLOT_WEIGHTS.get(slot_name, 1.0)

                    tentative_outfit = {
                        s: i for s, i in zip(
                            valid_slot_names[:len(items) + 1],
                            items + [curr]
                        )
                    }
                    
                    # Apply user feedback learning (reinforcement)
                    feedback_modifier = 0.0
                    if user_feedback:
                        curr_id = str(c["item"]["meta"].get("id", ""))
                        
                        # Penalty for disliked items
                        if curr_id in user_feedback['disliked_items']:
                            feedback_modifier -= 0.3
                            print(f"⚠️ Applying penalty for disliked item: {curr_id}")
                        
                        # Bonus for liked items
                        if curr_id in user_feedback['liked_items']:
                            feedback_modifier += 0.2
                            print(f"✨ Applying bonus for liked item: {curr_id}")
                        
                        # Check item pair preferences
                        for prev_item in items:
                            prev_id = str(prev_item["meta"].get("id", ""))
                            pair = tuple(sorted([prev_id, curr_id]))
                            
                            if pair in user_feedback['item_pairs']:
                                pair_score = user_feedback['item_pairs'][pair]
                                if pair_score < 0:
                                    feedback_modifier -= 0.4  # Strong penalty for disliked pairs
                                    print(f"❌ Penalizing disliked pair: {pair}")
                                elif pair_score > 0:
                                    feedback_modifier += 0.3  # Bonus for liked pairs
                                    print(f"💚 Boosting liked pair: {pair}")

                    ocs = compute_outfit_consistency(
                        tentative_outfit,
                        intent=template["intent"],
                        weather=weather
                    )
                    if "rain" in weather["condition"].lower():
                        if ocs["score"] < 0.75:
                            continue

                    ocs_score = ocs["score"]
                    # print("🧪 OCS Score so far:", ocs_score)
                    base_score = (
                        score * 0.35
                        + (c["score"] * slot_weight) * 0.25
                        + compatibility * 0.25
                    )

                    new_score = base_score * (0.6 + 0.4 * ocs_score) + feedback_modifier


                                       
                    next_beam.append((new_score, items + [curr]))
            
            beam = sorted(next_beam, key=lambda x: x[0], reverse=True)[:self.BEAM_WIDTH]

        if not beam: return {}
        best_score = -1e9
        best_outfit = None

        for score, items in beam:
            outfit = {s: i for s, i in zip(valid_slot_names, items)}
            rule_bonus = apply_outfit_rules(outfit, template_name)
            confidence = compute_confidence(
    outfit, template_name, weather, self.store.vectors
)["score"]
    #         ocs = compute_outfit_consistency(
    # outfit=outfit,
    # intent=template["intent"],
    # weather=weather
        #       )           
            # print("🧪 OCS:", ocs)

            # x

            final_score = final_score = (
    score * 0.7
    + confidence * 0.3
)


            if final_score > best_score:
                best_score = final_score
                best_outfit = outfit

        outfit = best_outfit

        confidence = compute_confidence(
    outfit=outfit,
    template_name=template_name,
    weather=weather,
    vectors=self.store.vectors
)       
        

        confidence_score = confidence["score"]
        # if confidence_score < CONFIDENCE_THRESHOLDS["minimum"]:
        #     print("⚠️ Outfit rejected due to low confidence.")
        #     return {}
        
        explanations = ExplanationEngine.explain(
    outfit=outfit,
    confidence=confidence,
    template_name=template_name,
    weather=weather
)
        print("\n📝 Why this outfit works:")
        for r in explanations:
            print("•", r)


        confidence_breakdown = confidence["breakdown"]


        print(f"🧠 Confidence Score: {confidence_score:.2f}")

        print(f"✨ Outfit Found (Score: {best_score:.3f})")
        for r in explain_outfit(outfit):
            print("•", r)

        if not outfit:
            print("⚠️ Could not assemble a valid outfit.")
            return {}

        # --- SHOPPING ANALYSIS ---
        upgrade_msg = self.shopper.find_upgrade(outfit, best_score, q_vec)
        if upgrade_msg:
            print(f"💡 SHOPPING INSIGHT: {upgrade_msg}")
        
#         Visualizer.show_outfit(
#     outfit,
#     title=f"{user_query} ({weather['condition']}) — Confidence: {confidence_score:.2f}",
#     recommendation=upgrade_msg
# )
        if DEBUG_REASONING:
            print("\n🔍 Candidate diagnostics:")
            for slot, candidates in candidates_map.items():
                print(f"\nSlot: {slot}")
                for c in candidates[:3]:
                    meta = c["item"]["meta"]
                    print(
                        f"  - {meta['sub_category']} | "
                        f"Color: {meta['primary_color']} | "
                        f"Score: {c['score']:.2f}"
                    )


        # Return outfit with metadata
        return {
            'outfit': outfit,
            'confidence': confidence,
            'weather': weather,
            'shopping_tip': upgrade_msg,
            'template': template_name
        }
    

if __name__ == "__main__":
    db = WardrobeStore(data_dir="my_wardrobe copy/data")
    planner = ProPlannerV7(store=db)
    
    # TEST: Ask for a Formal Outfit (Should trigger belt logic if you have accessories)
    planner.plan("sunday casual day outfit")