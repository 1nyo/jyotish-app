# calc/d9.py
from typing import Dict
from .base import deg_in_sign, house_from_signs
from .varga import d9_sign

def build_d9(asc_lon: float, planets: Dict[str,Dict]) -> Dict:
    asc_sign, asc_deg = deg_in_sign(asc_lon)
    asc_d9 = d9_sign(asc_sign, asc_deg)
    out = {"Asc":{"sign": asc_d9}, "planets":{}}
    for p, dat in planets.items():
        s, d = deg_in_sign(dat["lon"])
        vs = d9_sign(s, d)
        out["planets"][p] = {"sign": vs, "house": house_from_signs(asc_d9, vs)}
    return out
