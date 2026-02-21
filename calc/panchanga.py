# calc/panchanga.py
from typing import Tuple

TITHI_NAMES_CORE = [
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodasi","Chaturdasi"
]
# 15番は満月／新月
FULL_MOON = "Purnima"
NEW_MOON  = "Amavasya"

def _norm360(x: float) -> float:
    return x % 360.0

def tithi_from_elongation(delta_deg: float) -> Tuple[str, str, int]:
    """
    delta_deg: (Moon_lon - Sun_lon) in degrees, normalized to [0,360)
    returns (paksha, tithi_name, tithi_number[1..30])
    1..15  => Shukla; 16..30 => Krishna
    15 => Purnima, 30 => Amavasya
    """
    d = _norm360(delta_deg)
    tithi_no = int(d // 12.0) + 1  # 1..30
    if tithi_no <= 15:
        paksha = "Shukla"
        if tithi_no == 15:
            tname = FULL_MOON
        else:
            tname = TITHI_NAMES_CORE[tithi_no-1]
    else:
        paksha = "Krishna"
        k = tithi_no - 15
        if tithi_no == 30:
            tname = NEW_MOON
        else:
            tname = TITHI_NAMES_CORE[k-1]
    return paksha, tname, tithi_no
