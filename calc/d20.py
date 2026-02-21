# calc/d20.py
from .base import deg_in_sign, house_from_signs, EXALTATION_SIGN
from .varga import d20_sign

def build_d20(asc_lon: float, planets: Dict[str,Dict]) -> Dict:
    asc_sign, asc_deg = deg_in_sign(asc_lon)
    asc_v = d20_sign(asc_sign, asc_deg)
    out = {"Asc":{"sign": asc_v}, "planets":{}}
    for p, dat in planets.items():
        s, d = deg_in_sign(dat["lon"])
        vs = d20_sign(s, d)
        one = {"sign": vs, "house": house_from_signs(asc_v, vs)}
        if EXALTATION_SIGN.get(p) == vs:
            one["exalted"] = True
        out
