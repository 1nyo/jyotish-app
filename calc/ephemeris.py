# calc/ephemeris.py
from typing import Dict, Literal, Tuple, Any
import swisseph as swe


def setup_sidereal(ayanamsha: Literal["Lahiri_ICRC", "Lahiri"] = "Lahiri_ICRC") -> None:
    """
    Swiss Ephemeris をサイデリアル（Lahiri ICRC 優先）に設定。
    環境に SIDM_LAHIRI_ICRC が無い場合は Lahiri にフォールバック。
    """
    if ayanamsha == "Lahiri_ICRC" and hasattr(swe, "SIDM_LAHIRI_ICRC"):
        swe.set_sid_mode(getattr(swe, "SIDM_LAHIRI_ICRC"), 0, 0)
    else:
        # getattr(..., 1) は古い環境における保険。通常は swe.SIDM_LAHIRI が存在する。
        swe.set_sid_mode(getattr(swe, "SIDM_LAHIRI", 1), 0, 0)


def jd_ut_from_local(y: int, m: int, d: int, h_float: float, tz_hours: float) -> float:
    """
    ローカル時刻（タイムゾーンオフセット付き）から UT のユリウス日を算出。
    h_float は 24 時間制の小数（例：14:30 -> 14.5）
    """
    jd_local = swe.julday(y, m, d, h_float, swe.GREG_CAL)
    return jd_local - tz_hours / 24.0


def ayanamsa_deg(jd_ut: float) -> float:
    """
    現在設定のアヤナーンシャ（度）を返す。
    pyswisseph の版差により get_ayanamsa_ex_ut の戻り値が
      - (ayan, iflag)         # 2 要素
      - (retflag, ayan, serr) # 3 要素
    のいずれかになるため、長さに応じて安全に取り出す。
    例外発生時は get_ayanamsa_ut にフォールバック。
    """
    try:
        res: Any = swe.get_ayanamsa_ex_ut(jd_ut, 0)
        if isinstance(res, tuple):
            if len(res) == 2:
                ayan, _iflag = res
                return float(ayan)
            if len(res) == 3:
                _retflag, ayan, _serr = res
                return float(ayan)
            if len(res) == 1:
                return float(res[0])
        # 想定外でも 0 番目を試みる（ほぼ来ないはず）
        return float(res[0])  # type: ignore[index]
    except Exception:
        # 旧 API：単値（度）を返すため安全
        return float(swe.get_ayanamsa_ut(jd_ut))


def _norm360(x: float) -> float:
    """0–360 の範囲に正規化。"""
    return x % 360.0


def asc_sidereal(jd_ut: float, lat: float, lon: float) -> float:
    """
    サイデリアル Whole Sign の Asc を取得。
    pyswisseph の houses_ex は実装差があり、以下 2 通りを試す：
      1) houses_ex(jd, lat, lon, hsys[, iflag])   ← Python 拡張で一般的
      2) houses_ex(jd, iflag, lat, lon, hsys)     ← 一部バインディング
    戻り値の ascmc[0] が Asc（deg）。
    """
    hsys = b"W"
    try:
        # パターン1：jd, lat, lon, hsys, iflag
        _houses, ascmc = swe.houses_ex(jd_ut, lat, lon, hsys, swe.FLG_SIDEREAL)
    except TypeError:
        # パターン2：jd, iflag, lat, lon, hsys
        _houses, ascmc = swe.houses_ex(jd_ut, swe.FLG_SIDEREAL, lat, lon, hsys)
    return _norm360(ascmc[0])  # Asc


def planet_sidereal_longitudes(
    jd_ut: float, node_type: Literal["True", "Mean"] = "True"
) -> Dict[str, Dict[str, float]]:
    """
    各天体のサイデリアル地心黄経（deg）と速度（deg/day）を返す。
    速度は Swiss Ephemeris の正味値（符号付き）。Ketu は Rahu に 180°加算・速度符号反転。

    Returns:
      {
        "Su": {"lon": ..., "speed": ...},
        "Mo": {"lon": ..., "speed": ...},
        "Me": {"lon": ..., "speed": ...},
        "Ve": {"lon": ..., "speed": ...},
        "Ma": {"lon": ..., "speed": ...},
        "Ju": {"lon": ..., "speed": ...},
        "Sa": {"lon": ..., "speed": ...},
        "Ra": {"lon": ..., "speed": ...},
        "Ke": {"lon": ..., "speed": ...}
      }
    """
    res: Dict[str, Dict[str, float]] = {}

    # サイデリアル + 速度つき計算
    flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    node_body = swe.TRUE_NODE if node_type == "True" else swe.MEAN_NODE
    body_map: Dict[str, int] = {
        "Su": swe.SUN,
        "Mo": swe.MOON,
        "Me": swe.MERCURY,
        "Ve": swe.VENUS,
        "Ma": swe.MARS,
        "Ju": swe.JUPITER,
        "Sa": swe.SATURN,
        "Ra": node_body,
        "Ke": node_body,  # Ketu は後で 180°加算・速度反転
    }

    for key, body in body_map.items():
        xx, _ret = swe.calc_ut(jd_ut, body, flag)
        lon = _norm360(xx[0])
        spd = float(xx[3])
        if key == "Ke":
            lon = _norm360(lon + 180.0)
            spd = -spd
        res[key] = {"lon": float(lon), "speed": spd}

    return res
