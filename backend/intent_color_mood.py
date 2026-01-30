# intent_color_mood.py

from ontology import StyleIntent

INTENT_COLOR_MOOD = {
    StyleIntent.FORMAL_EVENT: {
        "Black", "Navy", "Charcoal", "Grey", "White", "Burgundy"
    },

    StyleIntent.SMART_CASUAL: {
        "Navy", "Olive", "Beige", "Brown", "White", "Grey"
    },

    StyleIntent.CASUAL_DAY: {
        "White", "Blue", "Grey", "Black", "Olive", "Tan"
    },

    StyleIntent.STREET: {
        "Black", "White", "Red", "Green", "Blue"
    },

    StyleIntent.LOUNGE: {
        "Grey", "Beige", "Cream", "Brown"
    },

    StyleIntent.LAYERED_COLD: {
        "Black", "Grey", "Navy", "Brown", "Olive"
    },
}

def color_mood_bias(item: dict, intent: StyleIntent) -> float:
    meta = item.get("meta", {})
    color = meta.get("primary_color")

    if not color:
        return 1.0

    preferred_colors = INTENT_COLOR_MOOD.get(intent, set())

    if color in preferred_colors:
        return 1.05   # weaker than formality bias

    return 0.98
