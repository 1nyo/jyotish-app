# calc/ephemeris.py
from typing import Dict, Literal
import swisseph as swe
from .base import norm360

SIDM_FALLBACK = getattr(swe, "SIDM_LAHIRI", 1)

def setup_sidereal(ayanamsha: Literal["Lahiri_ICRC","Lahiri"]="Lahiri_ICRC"):
    if ayanamsha == "Lahiri_ICRC" and hasattr(swe, "SIDM_LAHIRI_ICRC"):
        swe.set_sid_mode(getattr(swe,"SIDM_LAHIRI_ICRC"), 0, 0)
    else:
        swe.set_sid_mode(SIDM_FALLBACK, 0, 0)

def jd_ut_from_local(y,m,d,h_float,tz_hours: float) -> float:
    jd = swe.julday(y,m,d,h_float, swe.GREG_CAL)
    return jd - tz_hours/24.0

def ayanamsa_deg(jd_ut: float) -> float:
    # Return current ayanamsa in degrees
    val = swe.get_ayanamsa_ex_ut(jd_ut, 0)[1]  # (ret, ayan, serr)
    return val

def asc_sidereal(jd_ut: float, lat: float, lon: float) -> float:
    # Whole-sign houses; sidereal flag to get sidereal houses directly
    _, ascmc = swe.houses_ex(jd_ut, swe.FLG_SIDERAL, lat, lon, b"W")
    # ascmc[0] is Asc (sidereal) per docs
    return norm360(ascmc[0])

def planet_sidereal_longitudes(jd_ut: float, node_type: Literal["True","Mean"]="True") -> Dict[str, Dict]:
    res = {}
    flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    body_map = {
        "Su": swe.SUN, "Mo": swe.MOON, "Me": swe.MERCURY, "Ve": swe.VENUS,
        "Ma": swe.MARS, "Ju": swe.JUPITER, "Sa": swe.SATURN,
        "Ra": swe.TRUE_NODE if node_type=="True" else swe.MEAN_NODE,
        "Ke": swe.TRUE_NODE if node_type=="True" else swe.MEAN_NODE, # Ketu = opposite
    }
    for k, body in body_map.items():
        xx, _ = swe.calc_ut(jd_ut, body, flag)
        lon = norm360(xx[0])
        spd = xx[3]  # speed in longitude (deg/day)
        if k == "Ke":
            lon = norm360(lon + 180.0)
            spd = -spd
        res[k] = {"lon": lon, "speed": spd}
    return res
``
