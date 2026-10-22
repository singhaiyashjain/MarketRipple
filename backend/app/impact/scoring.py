"""Path strength, sign propagation, node polarity. OWNER: M3
strength = product(edge weights)  -> RELATIVE strength, never a probability."""
import re


def path_strength(weights: list[float]) -> float:
    s = 1.0
    for w in weights:
        s *= w
    return round(s, 4)


def terminal_effect(signs: list[int]) -> str:
    """Multiply signs along path; any 0 (mixed) makes result 'mixed'."""
    if any(s == 0 for s in signs):
        return "mixed"
    prod = 1
    for s in signs:
        prod *= s
    return "positive" if prod > 0 else "negative"


# --- polarity: does a RISE in this node hurt the sector it belongs to? -------------------------
# Sign propagation tells us whether a variable goes UP or DOWN. For the UI we need good/bad:
# 'Logistics Costs' going up is adverse, 'Oil Producers' Revenue' going up is favourable.
# Override per node by adding  "adverse_when_up": true/false  in data/seed_nodes.json (M4 can tune it).
_ADVERSE_LABEL = re.compile(r"cost|bill|deficit|inflation", re.I)


def adverse_when_up(node_attrs: dict) -> bool:
    explicit = node_attrs.get("adverse_when_up")
    if explicit is not None:
        return bool(explicit)
    return bool(_ADVERSE_LABEL.search(node_attrs.get("label", "")))


def flip_effect(effect: str) -> str:
    return {"positive": "negative", "negative": "positive"}.get(effect, effect)
