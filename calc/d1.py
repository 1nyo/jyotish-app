# calc/d1.py
from typing import Dict
from .base import deg_in_sign, house_from_signs, nakshatra_pada, round2, EXALTATION_SIGN
from .speed import flags as speed_flags
from .chara_karaka import compute_chara_karaka
from .lordship import planet_lordship

def build_d1(asc_lon: float, planets: Dict[str,Dict], opts: Dict) -> Dict:
    asc_sign, asc_deg = deg_in_sign(asc_lon)
    asc_nak, asc_pada = nakshatra_pada(asc_lon)
    out = {
        "Asc": {"sign": asc_sign, "degree": round2(asc_deg), "nakshatra": f"{asc_nak}-{asc_pada}" },
        "planets": {}
    }
    for p, dat in planets.items():
        s, d = deg_in_sign(dat["lon"])
        one = {"sign": s, "house": house_from_signs(asc_sign, s)}
        if p != "Ra" and p != "Ke":
            one["degree"] = round2(d)
            nk, pa = nakshatra_pada(dat["lon"])
            one["nakshatra"] = f"{nk}-{pa}"
        sp = speed_flags(p, dat["speed"], opts.get("speed_thresh", {}))
        if sp.get("retrograde"):
            one["retrograde"] = True
        if EXALTATION_SIGN.get(p) == s:
            one["exalted"] = True
        if p == "Mo":
            one["speed"] = sp["speed"]  # 仕様例に合わせ月のspeed表示
        out["planets"][p] = one

    # Jaimini
    if opts.get("ck_mode"):  # "7" or "8"
        pl_lons = {k: v["lon"] for k,v in planets.items()}
        ck = compute_chara_karaka(pl_lons, use_eight=(opts["ck_mode"]=="8"))
        # Karakamsa sign from D9 of AK: app側で D9計算後に注入する運用でもOK
        out["jaimini"] = {k: v["planet"] for k,v in ck.items()}

    # Lordship / Aspects
    if opts.get("include_lordship", True):
        out["lordship"] = planet_lordship(asc_sign)

    return out
