# consistency.py

from collections import Counter
from ontology import StyleIntent

PRECIPITATION_SENSITIVITY = {
    # footwear
    "Sandals": 0.0,
    "Slides": 0.0,
    "Flip Flops": 0.0,
    "Espadrilles": 0.2,
    "Sneakers": 0.6,
    "Chelsea Boots": 1.0,
    "Chukka Boots": 0.9,
    "Oxfords": 0.9,

    # tops / outerwear
    "Linen Shirt": 0.3,
    "Cotton Shirt": 0.6,
    "Hoodie": 0.9,
    "Sweater": 1.0,
    "Rain Jacket": 1.0,
    "Puffer Jacket": 0.7,

    # bottoms
    "Shorts": 0.2,
    "Jeans": 0.7,
    "Chinos": 0.8,
    "Cargo Pants": 0.9,
}

WATER_RESISTANCE = {
    # High Resistance (Great for Rain)
    "Rain Jacket": 1.0, "Trench Coat": 1.0, "Parka": 1.0, 
    "Puffer Jacket": 0.9, "Field Jacket": 0.9, "Shell": 1.0,
    
    # Moderate (Okay for drizzle)
    "Leather Jacket": 0.6, "Pea Coat": 0.5, "Overcoat": 0.5,
    "Bomber Jacket": 0.5, "Waxed Jacket": 0.9,
    
    # Low (Avoid in Rain)
    "Blazer": 0.2, "Denim Jacket": 0.1, "Cardigan": 0.0, 
    "Fleece": 0.1, "Hoodie": 0.2
}

SEASON_WEIGHT = {
    "Summer": 0,
    "Spring": 0.5,
    "All-Season": 1,
    "Fall": 1.5,
    "Winter": 2
}
MATERIAL_WEIGHT = {
    "Linen": 0,
    "Cotton": 0.5,
    "Denim": 1,
    "Wool": 1.5,
    "Leather": 2,
    "Puffer": 2.5
}
FUNCTION_ROLE = {
    "T-Shirt": "Base",
    "Shirt": "Base",
    "Cardigan": "Layer",
    "Sweater": "Layer",
    "Jacket": "Outer",
    "Coat": "Outer"
}
INTENT_FORMALITY = {
    StyleIntent.FORMAL_EVENT: {"Formal"},
    StyleIntent.SMART_CASUAL: {"Smart Casual", "Formal"},
    StyleIntent.CASUAL_DAY: {"Casual", "Smart Casual"}
}

INTENT_FORMALITY_MAP = {
    "Casual Day": {"Casual", "Smart Casual"},
    "Smart Casual": {"Smart Casual"},
    "Formal Event": {"Formal"},
    "Street": {"Casual"},
    "Layered Cold": {"Casual", "Smart Casual"},
}

def is_precipitating(weather):
    condition = weather.get("condition", "").lower()
    return any(k in condition for k in ["rain", "drizzle", "storm", "shower"])

# In consistency.py

# Add this configuration dictionary at the top
WATER_RESISTANCE = {
    # High Resistance (Great for Rain)
    "Rain Jacket": 1.0, "Trench Coat": 1.0, "Parka": 1.0, 
    "Puffer Jacket": 0.9, "Field Jacket": 0.9, "Shell": 1.0,
    
    # Moderate (Okay for drizzle)
    "Leather Jacket": 0.6, "Pea Coat": 0.5, "Overcoat": 0.5,
    "Bomber Jacket": 0.5, "Waxed Jacket": 0.9,
    
    # Low (Avoid in Rain)
    "Blazer": 0.2, "Denim Jacket": 0.1, "Cardigan": 0.0, 
    "Fleece": 0.1, "Hoodie": 0.2
}

# In consistency.py -> Replace compute_season_consistency

def compute_season_consistency(outfit, weather):
    temp = weather.get("temp", 20)
    raining = "rain" in weather.get("condition", "").lower()
    
    scores = []
    
    # 1. DEFINE THERMAL LIMITS
    # Items that cause overheating > 15°C (59°F)
    HOT_BANS = ["puffer", "shearling", "heavy wool", "thermal", "glove", "scarf", "beanie"]
    
    # Items that cause freezing < 10°C (50°F)
    COLD_BANS = ["linen", "shorts", "sandal", "tank", "flip flop", "slide"]

    for item in outfit.values():
        meta = item["meta"]
        sub = meta.get("sub_category", "").lower()
        mat = meta.get('material', '').lower()
        
        # A. STRICT THERMAL CHECKS
        if temp > 18.0: 
            if any(x in sub for x in HOT_BANS): return 0.0  # HARD FAIL (Heatstroke)
        
        if temp < 10.0:
            if any(x in sub for x in COLD_BANS): return 0.0 # HARD FAIL (Hypothermia)

        # B. RAIN CHECK (Existing logic, slightly tuned)
        if raining:
            if sub in ["sandals", "slides", "flip flops", "suede shoes"]:
                return 0.2  # Soft Fail
            if meta.get("category") == "Outerwear":
                # Check for water resistance keywords
                if any(x in sub for x in ["rain", "trench", "parka", "shell", "technical"]):
                    scores.append(1.0)
                else:
                    scores.append(0.5) # Regular coat in rain is "meh"
        
        scores.append(1.0) # Default pass if no bans triggered

    return sum(scores) / len(scores) if scores else 0.0

def compute_material_harmony(outfit):
    materials = [i["meta"].get("material") for i in outfit.values()]

    winter_materials = {"Wool", "Leather", "Fleece"}
    summer_materials = {"Linen", "Cotton"}

    if any(m in winter_materials for m in materials) and \
       any(m in summer_materials for m in materials):
        return 0.4

    return 1.0

# In consistency.py -> Replace compute_redundancy

def compute_redundancy(outfit):
    # Words we NEVER want to repeat in an outfit
    # e.g. "Denim Jacket" + "Denim Jeans" = Canadian Tuxedo (Risk)
    # e.g. "Flannel Shirt" + "Flannel Shacket" = Redundant
    DANGER_PATTERNS = {"flannel", "denim", "leather", "corduroy", "linen", "plaid", "stripe"}
    
    found_patterns = []
    penalty = 0.0
    
    for item in outfit.values():
        name = item['meta'].get('sub_category', '').lower()
        
        # Check for danger patterns
        for pattern in DANGER_PATTERNS:
            if pattern in name:
                if pattern in found_patterns:
                    # We found a duplicate! (e.g. Flannel twice)
                    penalty += 0.4 
                found_patterns.append(pattern)
                
    # Also check for exact duplicate sub-categories (e.g. Hoodie + Hoodie)
    subs = [i['meta'].get('sub_category') for i in outfit.values()]
    if len(subs) != len(set(subs)):
        penalty += 0.2

    return max(0.0, 1.0 - penalty)

def compute_intent_alignment(outfit, intent):
    allowed = INTENT_FORMALITY_MAP.get(intent.value, set())
    if not allowed:
        return 0.5

    matches = 0
    for item in outfit.values():
        f = item["meta"].get("formality")
        if f in allowed:
            matches += 1

    return matches / len(outfit)

def compute_environment_safety(outfit, weather):
    condition = weather["condition"].lower()

    for item in outfit.values():
        sub = item["meta"]["sub_category"].lower()

        if "rain" in condition and "sandal" in sub:
            return 0.0

    return 1.0



def compute_outfit_consistency(outfit, intent, weather):
    season = compute_season_consistency(outfit, weather=weather)
    material = compute_material_harmony(outfit)
    redundancy = compute_redundancy(outfit)
    intent_score = compute_intent_alignment(outfit, intent)
    environment = compute_environment_safety(outfit, weather)

    score = (
        season * 0.25 +
        material * 0.20 +
        redundancy * 0.20 +
        intent_score * 0.20 +
        environment * 0.15
    )

    return {
        "score": round(score, 3),
        "breakdown": {
            "season": season,
            "material": material,
            "redundancy": redundancy,
            "intent": intent_score,
            "environment": environment,
        }
    }
