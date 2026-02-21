# calc/speed.py
from typing import Dict

# ===== user-provided thresholds (deg/day) =====
TH = {
    # Moon bands
    "MOON_VERY_SLOW": 12.0,
    "MOON_SLOW":      12.2,
    "MOON_FAST":      14.8,
    "MOON_VERY_FAST": 15.1,
    # Station / Fast (others)
    "MERCURY_STATION": 0.20,
    "MERCURY_VERY_FAST": 1.60,
    "VENUS_STATION":   0.15,
    "VENUS_FAST":      1.15,
    "MARS_STATION":    0.08,
    "MARS_FAST":       0.65,
    "JUPITER_STATION": 0.03,
    "JUPITER_FAST":    0.20,
    "SATURN_STATION":  0.02,
    "SATURN_FAST":     0.11,
    "RAHU_STATION":    0.01,
    "RAHU_FAST":       0.06,
}

def moon_flags(speed: float) -> Dict[str, bool|float]:
    out: Dict[str,bool|float] = {}
    s = abs(speed)
    if s <= TH["MOON_VERY_SLOW"]:
        out["very_slow"] = True
    elif s <= TH["MOON_SLOW"]:
        out["slow"] = True
    elif s >= TH["MOON_VERY_FAST"]:
        out["very_fast"] = True
    elif s >= TH["MOON_FAST"]:
        out["fast"] = True
    out["speed"] = round(speed, 3)
    return out

def planet_flags(planet: str, speed: float) -> Dict[str,bool]:
    out: Dict[str,bool] = {}
    s = abs(speed)
    if planet == "Me":
        if s <= TH["MERCURY_STATION"]: out["station"] = True
        if s >= TH["MERCURY_VERY_FAST"]: out["very_fast"] = True
    elif planet == "Ve":
        if s <= TH["VENUS_STATION"]: out["station"] = True
        if s >= TH["VENUS_FAST"]: out["fast"] = True
    elif planet == "Ma":
        if s <= TH["MARS_STATION"]: out["station"] = True
        if s >= TH["MARS_FAST"]: out["fast"] = True
    elif planet == "Ju":
        if s <= TH["JUPITER_STATION"]: out["station"] = True
        if s >= TH["JUPITER_FAST"]: out["fast"] = True
    elif planet == "Sa":
        if s <= TH["SATURN_STATION"]: out["station"] = True
        if s >= TH["SATURN_FAST"]: out["fast"] = True
    elif planet == "Ra" or planet == "Ke":
        if s <= TH["RAHU_STATION"]: out["station"] = True
        if s >= TH["RAHU_FAST"]: out["fast"] = True
    return out

def flags(planet: str, speed: float) -> Dict[str, bool|float]:
    out: Dict[str,bool|float] = {}
    if speed < 0:
        out["retrograde"] = True
    if planet == "Mo":
        out.update(moon_flags(speed))
    else:
        pf = planet_flags(planet, speed)
        out.update(pf)
        # B: いずれかの速度フラグが True の場合のみ、数値速度(3桁)も出力
        if any(pf.values()):
            out["speed"] = round(speed, 3)
    return out
