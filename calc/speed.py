# calc/speed.py
from typing import Dict

DEFAULT_THRESH = {
    # deg/day thresholds (heuristic;可変)
    "station": 0.01,
    "moon_fast": 14.5,   # very fast if > this
}

def flags(planet: str, speed: float, thresh: Dict[str,float]=DEFAULT_THRESH) -> Dict[str,bool|float]:
    out = {}
    if speed < 0:
        out["retrograde"] = True
    if abs(speed) < thresh["station"]:
        out["station"] = True
    if planet == "Mo" and speed > thresh["moon_fast"]:
        out["very_fast"] = True
    out["speed"] = round(speed, 3)
    return out
