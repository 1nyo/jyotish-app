# calc/d60.py
from .base import deg_in_sign, house_from_signs
from .varga import d60_sign

def build_d60(asc_lon: float, planets: Dict[str,Dict]) -> Dict:
    asc_sign, asc_deg = deg_in_sign(asc_lon)
    asc_v = d60_sign(asc_sign, asc_deg)
    out = {"Asc":{"sign": asc_v}, "planets":{}}
    for p, dat in planets.items():
        s, d = deg_in_sign(dat["lon"])
        vs = d60_sign(s, d)
        out["planets"][p] = {"sign": vs, "house": house_from_signs(asc_v, vs)}
    return out
