from enum import Enum

class Category(str, Enum):
    TOP = "Top"
    BOTTOM = "Bottom"
    FOOTWEAR = "Footwear"
    OUTERWEAR = "Outerwear"
    ONE_PIECE = "One-Piece"
    ACCESSORY = "Accessory"

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

# Rules for what constitutes a valid outfit structure
OUTFIT_TEMPLATES = {
    "basic": [Category.TOP, Category.BOTTOM, Category.FOOTWEAR],
    "layered": [Category.TOP, Category.BOTTOM, Category.OUTERWEAR, Category.FOOTWEAR],
    "one_piece": [Category.ONE_PIECE, Category.FOOTWEAR]
}