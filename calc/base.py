# calc/base.py
from dataclasses import dataclass
from typing import Dict, Tuple

SIGNS = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
SIGN_INDEX = {s:i for i,s in enumerate(SIGNS)}

# 4-letter Nakshatra codes (per user pref; Ashlesha -> 'Asre')
NAK_CODES = [
    "Ashv","Bhar","Krit","Rohi","Mrig","Ardr","Puna","Push","Asre",
    "Magh","PPha","UPha","Hast","Chit","Swat","Vish","Anur","Jyes",
    "Mula","PAsh","UAsh","Shra","Dhan","Sata","PBha","UBha","Reva",
]

NAK_SIZE = 13 + 20/60      # 13°20'
PADA_SIZE = 3 + 20/60      # 3°20'

EXALTATION_SIGN = {
    "Su":"Ar","Mo":"Ta","Ma":"Cp","Me":"Vi","Ju":"Cn","Ve":"Pi","Sa":"Li"
}

PLANETS = ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]

def norm360(x: float) -> float:
    return x % 360.0

def deg_in_sign(lon: float) -> Tuple[str, float]:
    """Return (sign_abbr, degree_in_sign[0..30)) for sidereal ecliptic longitude."""
    lon = norm360(lon)
    si = int(lon // 30)
    deg = lon - si*30
    return SIGNS[si], deg

def house_from_signs(asc_sign: str, obj_sign: str) -> int:
    """Whole-sign house number (1..12)."""
    a = SIGN_INDEX[asc_sign]
    b = SIGN_INDEX[obj_sign]
    return ((b - a) % 12) + 1

def nakshatra_pada(lon: float) -> Tuple[str, int]:
    """Return (nak_code, pada#1..4) from sidereal ecliptic longitude."""
    pos = norm360(lon)
    nak_index = int(pos // NAK_SIZE) % 27
    rem = pos - nak_index * NAK_SIZE
    pada = int(rem // PADA_SIZE) + 1
    return NAK_CODES[nak_index], pada

def round2(x: float) -> float:
    return float(f"{x:.2f}")
