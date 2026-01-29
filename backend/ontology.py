from enum import Enum
from typing import Dict, List, Optional


class Category(str, Enum):
    TOP = "Top"
    BOTTOM = "Bottom"
    FOOTWEAR = "Footwear"
    OUTERWEAR = "Outerwear"
    ONE_PIECE = "One-Piece"
    ACCESSORY = "Accessory"


class LayerRole(str, Enum):
    BASE = "Base"
    MID = "Mid"
    OUTER = "Outer"
    NONE = "None"


class Season(str, Enum):
    SUMMER = "Summer"
    WINTER = "Winter"
    SPRING = "Spring"
    FALL = "Fall"
    ALL_YEAR = "All-Season"


class Formality(str, Enum):
    CASUAL = "Casual"
    SMART_CASUAL = "Smart Casual"
    FORMAL = "Formal"
    LOUNGE = "Lounge"


class StyleIntent(str, Enum):
    CASUAL_DAY = "Casual Day"
    SMART_CASUAL = "Smart Casual"
    FORMAL_EVENT = "Formal Event"
    STREET = "Street"
    LAYERED_COLD = "Layered Cold"
    LOUNGE = "Lounge"


# Outfit Templates
OUTFIT_TEMPLATES: Dict[str, Dict] = {

    "basic": {
        "intent": StyleIntent.CASUAL_DAY,
        "slots": [
            {"category": Category.TOP, "required": True, "min": 1, "max": 1},
            {"category": Category.BOTTOM, "required": True, "min": 1, "max": 1},
            {"category": Category.FOOTWEAR, "required": True, "min": 1, "max": 1},
            {"category": Category.ACCESSORY, "required": False, "min": 0, "max": 1},
        ]
    },

    "smart_casual": {
        "intent": StyleIntent.SMART_CASUAL,
        "slots": [
            {"category": Category.TOP, "required": True, "min": 1, "max": 1},
            {"category": Category.BOTTOM, "required": True, "min": 1, "max": 1},
            {"category": Category.OUTERWEAR, "required": False, "min": 0, "max": 1},
            {"category": Category.FOOTWEAR, "required": True, "min": 1, "max": 1},
            {"category": Category.ACCESSORY, "required": False, "min": 0, "max": 2},
        ]
    },

    "formal": {
        "intent": StyleIntent.FORMAL_EVENT,
        "slots": [
            {"category": Category.TOP, "required": True, "min": 1, "max": 1},
            {"category": Category.BOTTOM, "required": True, "min": 1, "max": 1},
            {"category": Category.OUTERWEAR, "required": True, "min": 1, "max": 1},
            {"category": Category.FOOTWEAR, "required": True, "min": 1, "max": 1},
            {"category": Category.ACCESSORY, "required": True, "min": 1, "max": 2},
        ]
    },

    "layered": {
        "intent": StyleIntent.LAYERED_COLD,
        "slots": [
            {"category": Category.TOP, "required": True, "min": 1, "max": 1},
            {"category": Category.OUTERWEAR, "required": True, "min": 1, "max": 2},
            {"category": Category.BOTTOM, "required": True, "min": 1, "max": 1},
            {"category": Category.FOOTWEAR, "required": True, "min": 1, "max": 1},
            {"category": Category.ACCESSORY, "required": False, "min": 0, "max": 2},
        ]
    },

    "one_piece": {
        "intent": StyleIntent.FORMAL_EVENT,
        "slots": [
            {"category": Category.ONE_PIECE, "required": True, "min": 1, "max": 1},
            {"category": Category.FOOTWEAR, "required": True, "min": 1, "max": 1},
            {"category": Category.ACCESSORY, "required": False, "min": 0, "max": 2},
        ]
    }
}
