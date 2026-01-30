# intent_formality.py

from ontology import StyleIntent, Formality

INTENT_FORMALITY_MAP = {
    StyleIntent.CASUAL_DAY: {
        Formality.CASUAL,
        Formality.SMART_CASUAL,
    },
    StyleIntent.SMART_CASUAL: {
        Formality.SMART_CASUAL,
        Formality.CASUAL,
    },
    StyleIntent.FORMAL_EVENT: {
        Formality.FORMAL,
        Formality.SMART_CASUAL,
    },
    StyleIntent.STREET: {
        Formality.CASUAL,
    },
    StyleIntent.LAYERED_COLD: {
        Formality.CASUAL,
        Formality.SMART_CASUAL,
    },
    StyleIntent.LOUNGE: {
        Formality.LOUNGE,
        Formality.CASUAL,
    },
}

def formality_bias(item: dict, intent: StyleIntent) -> float:
    meta = item.get("meta", {})
    item_formality = meta.get("formality")

    if not item_formality:
        return 1.0

    try:
        item_formality = Formality(item_formality)
    except ValueError:
        return 1.0

    preferred = INTENT_FORMALITY_MAP.get(intent, set())

    if item_formality in preferred:
        return 1.08   # gentle nudge up

    return 0.96       # gentle nudge down
