# calc/varga.py
from typing import Tuple
from .base import SIGNS, SIGN_INDEX

def _movable_fixed_dual(sign: str) -> str:
    i = SIGN_INDEX[sign]
    if i in (0,3,6,9): return "movable"
    if i in (1,4,7,10): return "fixed"
    return "dual"

def d9_sign(sign: str, deg: float) -> str:
    # 9 parts each 3°20' = 3 + 20/60
    part = int((deg / 30.0) * 9)  # 0..8
    mfd = _movable_fixed_dual(sign)
    start = {
        "movable": SIGN_INDEX[sign],
        "fixed":   (SIGN_INDEX[sign] + 8) % 12,  # 9th from sign
        "dual":    (SIGN_INDEX[sign] + 4) % 12,  # 5th from sign
    }[mfd]
    idx = (start + part) % 12
    return SIGNS[idx]

def d20_sign(sign: str, deg: float) -> str:
    # 20 parts each 1°30'
    part = int((deg / 30.0) * 20)  # 0..19
    mfd = _movable_fixed_dual(sign)
    start_base = {"movable":0, "fixed":8, "dual":4}[mfd]  # Ar=0,Sg=8,Le=4
    idx = (start_base + part) % 12
    return SIGNS[idx]

def d60_sign(sign: str, deg: float) -> str:
    # classic JH-compatible formula: floor(deg*2) -> mod 12 -> +1
    n = int(deg * 2)  # 0..59
    shift = (n % 12) + 1
    idx = (SIGN_INDEX[sign] + shift - 1) % 12
    return SIGNS[idx]
