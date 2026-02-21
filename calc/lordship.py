# calc/lordship.py
from typing import Dict, List
from .base import SIGNS, SIGN_INDEX

# Classical sign rulers
RULER = {
    "Ar":"Ma","Ta":"Ve","Ge":"Me","Cn":"Mo","Le":"Su","Vi":"Me",
    "Li":"Ve","Sc":"Ma","Sg":"Ju","Cp":"Sa","Aq":"Sa","Pi":"Ju"
}

def planet_lordship(asc_sign: str) -> Dict[str, list]:
    """Return planet -> [houses it rules] under Whole Sign."""
    out = {p:[] for p in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]}
    for i, s in enumerate(SIGNS):
        lord = RULER[s]
        # house number if this sign is a house under given Asc
        house = ((i - SIGN_INDEX[asc_sign]) % 12) + 1
        out[lord].append(house)
    return out
