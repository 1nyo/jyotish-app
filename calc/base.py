# calc/base.py
from typing import Tuple, Dict

SIGNS = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

# JH名称（固定長にしない）
NAK_LABELS_JH = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu",
    "Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta",
    "Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
    "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati",
]
NAK_SIZE = 13 + 20/60
PADA_SIZE = 3 + 20/60

EXALTATION_SIGN: Dict[str,str] = {
    "Su":"Ar","Mo":"Ta","Ma":"Cp","Me":"Vi","Ju":"Cn","Ve":"Pi","Sa":"Li"
}
PLANETS = ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]

def norm360(x: float) -> float:
    return x % 360.0

def deg_in_sign(lon: float) -> Tuple[str, float]:
    lon = norm360(lon)
    si = int(lon // 30)
    return SIGNS[si], lon - si * 30

def house_from_signs(asc_sign: str, obj_sign: str) -> int:
    a = SIGN_INDEX[asc_sign]; b = SIGN_INDEX[obj_sign]
    return ((b - a) % 12) + 1

def nakshatra_pada(lon: float, labels=None) -> Tuple[str, int]:
    """Return (nak_label, pada[1..4]) from sidereal ecliptic longitude."""
    labels = labels or NAK_LABELS_JH
    pos = norm360(lon)
    nak_index = int(pos // NAK_SIZE) % 27
    rem = pos - nak_index * NAK_SIZE
    pada = int(rem // PADA_SIZE) + 1
    return labels[nak_index], pada

def round2(x: float) -> float:
    return float(f"{x:.2f}")
