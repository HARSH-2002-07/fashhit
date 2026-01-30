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

def compute_season_consistency(outfit, weather):
    """
    Measures how suitable the outfit is for the climate:
    - Temperature checks
    - Rain functionality (Waterproofing)
    """
    temp = weather.get("temp", 20)
    if not outfit: return 0.0

    raining = is_precipitating(weather)
    scores = []

    for item in outfit.values():
        meta = item["meta"]
        sub = meta.get("sub_category", "")
        cat = meta.get("category", "")
        
        # --- 1. PRECIPITATION LOGIC (The "Waterproofing" Fix) ---
        precip_score = 1.0
        
        if raining:
            # Penalty for "Open" footwear (Sandals) - Existing
            if meta.get("sub_category") == "Shorts":
                precip_score = 0.3
            
            # NEW: Outerwear Functionality Check
            if cat == "Outerwear":
                # Default to 0.4 if unknown (risky), look up known types
                # Using substring matching to catch "Navy Blazer" -> "Blazer"
                res_score = 0.4 
                for key, val in WATER_RESISTANCE.items():
                    if key.lower() in sub.lower():
                        res_score = val
                        break
                precip_score = res_score

        # --- 2. TEMPERATURE LOGIC ---
        # Hard Safety Stop (No shorts in winter)
        unsafe_cold_items = ["Shorts", "Sandals", "Flip Flops", "Slides"]
        
        if any(x in sub for x in unsafe_cold_items) and temp < 20:
            return 0.0  # Hard Reject

        if temp < 10:
            temp_score = 1.0 if meta.get("seasonality") in ["Winter", "All-Season"] else 0.4
        elif temp > 25:
            temp_score = 1.0 if meta.get("seasonality") in ["Summer", "All-Season"] else 0.5
        else:
            temp_score = 1.0

        # Weighted item score
        if raining:
            # In rain, functionality matters more than temp
            scores.append(0.4 * temp_score + 0.6 * precip_score)
        else:
            scores.append(temp_score)

    if not scores: return 0.0
    
    # Return average score
    return sum(scores) / len(scores)

    return min(scores) * 0.6 + (sum(scores) / len(scores)) * 0.4

def compute_material_harmony(outfit):
    materials = [i["meta"].get("material") for i in outfit.values()]

    winter_materials = {"Wool", "Leather", "Fleece"}
    summer_materials = {"Linen", "Cotton"}

    if any(m in winter_materials for m in materials) and \
       any(m in summer_materials for m in materials):
        return 0.4

    return 1.0

def compute_redundancy(outfit):
    seen = set()
    penalty = 0.0

    for item in outfit.values():
        sub = item["meta"].get("sub_category")
        if sub in seen:
            penalty += 0.3
        seen.add(sub)

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
