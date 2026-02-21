# calc/chara_karaka.py
from typing import Dict, List, Tuple
from .base import PLANETS, deg_in_sign

KARAKA_7 = ["AK","AmK","BK","MK","PK","GK","DK"]
KARAKA_8 = ["AK","AmK","BK","MK","PK","GK","DK","PiK"]

def _ck_degree_for_rank(planet: str, lon: float) -> float:
    # rank by degree INSIDE SIGN (0..30). Rahu counts reversed (30 - deg)
    _, d = deg_in_sign(lon)
    if planet == "Ra":
        return 30.0 - d
    return d

def compute_chara_karaka(pl_lons: Dict[str,float], use_eight: bool=False) -> Dict[str,str]:
    # exclude Ketu from CK; include Rahu when use_eight=True
    cand = {p:pl_lons[p] for p in ["Su","Mo","Ma","Me","Ju","Ve","Sa"]}
    if use_eight:
        cand["Ra"] = pl_lons["Ra"]
    ranked = sorted(cand.items(), key=lambda kv: _ck_degree_for_rank(kv[0], kv[1]), reverse=True)
    roles = KARAKA_8 if use_eight else KARAKA_7
    out = {}
    for (p,_), role in zip(ranked, roles):
        out[role] = {"planet": p}
    return out
