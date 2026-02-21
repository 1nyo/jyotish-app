# calc/ephemeris.py
from typing import Dict, Literal
import swisseph as swe

def setup_sidereal(ayanamsha: Literal["Lahiri_ICRC","Lahiri"]="Lahiri_ICRC"):
    # Lahiri ICRC が無い環境では Lahiri にフォールバック
    if ayanamsha == "Lahiri_ICRC" and hasattr(swe, "SIDM_LAHIRI_ICRC"):
        swe.set_sid_mode(getattr(swe, "SIDM_LAHIRI_ICRC"), 0, 0)
    else:
        swe.set_sid_mode(getattr(swe, "SIDM_LAHIRI", 1), 0, 0)

def jd_ut_from_local(y: int, m: int, d: int, h_float: float, tz_hours: float) -> float:
    jd = swe.julday(y, m, d, h_float, swe.GREG_CAL)
    return jd - tz_hours/24.0

def ayanamsa_deg(jd_ut: float) -> float:
    # 現在のアヤナーンシャ（deg）
    ret, ayan, _ = swe.get_ayanamsa_ex_ut(jd_ut, 0)
    return ayan

def _norm360(x: float) -> float:
    return x % 360.0

def asc_sidereal(jd_ut: float, lat: float, lon: float) -> float:
    # サイデリアル Whole Sign の Asc を取得
    # → FLG_SIDEREAL（E が2つ）、ハウス方式は 'W'
    _, ascmc = swe.houses_ex(jd_ut, swe.FLG_SIDEREAL, lat, lon, 'W')
    return _norm360(ascmc[0])  # Asc

def planet_sidereal_longitudes(
    jd_ut: float, node_type: Literal["True","Mean"]="True"
) -> Dict[str, Dict]:
    """
    Returns:
      {
        "Su":{"lon":..., "speed":...},
        ...,
        "Ra":{"lon":..., "speed":...},
        "Ke":{"lon":..., "speed":...}
      }
    """
    res: Dict[str, Dict] = {}
    flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    node_body = swe.TRUE_NODE if node_type == "True" else swe.MEAN_NODE
    body_map = {
        "Su": swe.SUN, "Mo": swe.MOON, "Me": swe.MERCURY, "Ve": swe.VENUS,
        "Ma": swe.MARS, "Ju": swe.JUPITER, "Sa": swe.SATURN,
        "Ra": node_body,
        "Ke": node_body,  # Ketu は後で 180°加算
    }

    for k, body in body_map.items():
        xx, _ = swe.calc_ut(jd_ut, body, flag)
        lon = _norm360(xx[0])
        spd = xx[3]
        if k == "Ke":
            lon = _norm360(lon + 180.0)
            spd = -spd
        res[k] = {"lon": lon, "speed": spd}
    return res
