# calc/d1.py
from typing import Dict, Any
from .base import (
    deg_in_sign,
    house_from_signs,
    nakshatra_pada,
    round2,
    EXALTATION_SIGN,
)
from .speed import flags as speed_flags
from .chara_karaka import compute_chara_karaka
from .lordship import planet_lordship
from .panchanga import tithi_from_elongation


def build_d1(asc_lon: float, planets: Dict[str, Dict[str, float]], opts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build D1 (Rāśi) JSON object.

    Parameters
    ----------
    asc_lon : float
        Sidereal ecliptic longitude of Ascendant (deg, 0..360).
    planets : dict
        { "Su":{"lon":..., "speed":...}, "Mo":{"lon":..., "speed":...}, ..., "Ra":{}, "Ke":{} }
        - lon  : sidereal ecliptic longitude (deg, 0..360)
        - speed: ecliptic longitude speed (deg/day, Swiss Ephemeris)
    opts : dict
        {
          "ck_mode": "7" | "8",           # Jaimini Chara Karaka system
          "include_lordship": bool,       # include planet->houses rulership
        }

    Returns
    -------
    dict
        {
          "Asc": {...},
          "planets": { "Su": {...}, ... },
          "jaimini": {...},               # (if ck_mode provided)
          "lordship": {...}               # (if include_lordship True)
        }

    Notes
    -----
    - House system: Whole Sign
    - Nakshatra labels: JH英名（例：Uttara Bhadrapada）
    - Degree: 0.00–29.99, 小数2桁
    - retrograde / exalted は true の時のみ出力
    - Moon：常に speed(小数3桁) を出し、very_slow/slow/fast/very_fast を真の時のみ付与
    - 他惑星：station/fast/very_fast のいずれかが真の時のみ speed(3桁) を出力
    - Nodes(Ra/Ke)：degree/nakshatra は出力しない（house/signは出力）
    - 月に限り "paksha"（Shukla/Krishna） と "tithi"（Pratipada〜/Purnima/Amavasya）を付与
    - karakamsa_sign は app.py 側で D9 から注入してください
    """

    # ---- Ascendant ----
    asc_sign, asc_deg = deg_in_sign(asc_lon)
    asc_nak, asc_pada = nakshatra_pada(asc_lon)

    out: Dict[str, Any] = {
        "Asc": {
            "sign": asc_sign,
            "degree": round2(asc_deg),
            "nakshatra": f"{asc_nak}-{asc_pada}",
        },
        "planets": {}
    }

    # ---- keep Sun/Moon longitudes for Tithi ----
    sun_lon = planets.get("Su", {}).get("lon")
    moon_lon = planets.get("Mo", {}).get("lon")

    # ---- planets ----
    # 順序は dict の順でも問題ありません（LLM用途で意味的な整合を優先）
    for p, dat in planets.items():
        lon = float(dat["lon"])
        spd = float(dat["speed"])

        sign, deg = deg_in_sign(lon)
        one: Dict[str, Any] = {
            "sign": sign,
            "house": house_from_signs(asc_sign, sign),
        }

        # Nodes は degree/nakshatra を出さない
        if p not in ("Ra", "Ke"):
            one["degree"] = round2(deg)
            nk, pa = nakshatra_pada(lon)
            one["nakshatra"] = f"{nk}-{pa}"

        # 速度フラグ
        sp = speed_flags(p, spd)

        # retrograde（真のときのみ出力）
        if sp.get("retrograde"):
            one["retrograde"] = True

        # Moon：常時 speed（3桁）＋ 該当する速度バンドのみ出力
        if p == "Mo":
            if sp.get("speed") is not None:
                one["speed"] = sp["speed"]
            for key in ("very_slow", "slow", "fast", "very_fast"):
                if sp.get(key):
                    one[key] = True

            # Paksha / Tithi
            if sun_lon is not None and moon_lon is not None:
                delta = (moon_lon - sun_lon) % 360.0
                paksha, tname, _ = tithi_from_elongation(delta)
                one["paksha"] = paksha
                one["tithi"] = tname

        else:
            # 他惑星：station/fast/very_fast のいずれかが真なら speed を出力
            if sp.get("speed") is not None:
                one["speed"] = sp["speed"]
            for key in ("station", "fast", "very_fast"):
                if sp.get(key):
                    one[key] = True

        # exalted（真のときのみ）
        if EXALTATION_SIGN.get(p) == sign:
            one["exalted"] = True

        out["planets"][p] = one

    # ---- Jaimini Chara Karaka（7/8 切替）----
    ck_mode = (opts or {}).get("ck_mode")
    if ck_mode in ("7", "8"):
        pl_lons = {k: v["lon"] for k, v in planets.items()}
        ck = compute_chara_karaka(pl_lons, use_eight=(ck_mode == "8"))
        # 例：{"AK":{"planet":"Ma"}, ...} → {"AK":"Ma", ...}
        out["jaimini"] = {k: v["planet"] for k, v in ck.items()}

    # ---- Lordship（Whole Sign）----
    if (opts or {}).get("include_lordship", True):
        out["lordship"] = planet_lordship(asc_sign)

    return out
