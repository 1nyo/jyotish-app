import streamlit as st
import swisseph as swe
import json
from datetime import date, datetime, time, timezone, timedelta

# zoneinfo（標準）を優先。ない場合はフォールバック（固定オフセットのみ）
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

# ---------- 基本設定 ----------
st.set_page_config(page_title="AI Jyotish Data Generator", layout="wide")
st.title("🌌 AI専用ヴェーダ占星術データ抽出")

# 惑星キー短縮（デフォルトON）
PLANET_ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
    "Rahu": "Ra", "Ketu": "Ke", "Ascendant": "Asc"
}

# サイン略号（12個）
SIG_ABBR = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
            "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]

# 都市データ（必要に応じて追加OK）
# tz: IANA タイムゾーン名（DST自動判定に必須） / lat, lon: 緯度経度
# fallback_offset: zoneinfo が使えない場合の標準オフセット（時間）
CITY_DB = {
    "Tokyo, Japan":      {"tz": "Asia/Tokyo",        "lat": 35.6764, "lon": 139.6500, "fallback_offset": 9.0},
    "Osaka, Japan":      {"tz": "Asia/Tokyo",        "lat": 34.6937, "lon": 135.5023, "fallback_offset": 9.0},
    "Nagano, Japan":     {"tz": "Asia/Tokyo",        "lat": 36.6513, "lon": 138.1810, "fallback_offset": 9.0},
    "New York, USA":     {"tz": "America/New_York",  "lat": 40.7128, "lon": -74.0060, "fallback_offset": -5.0},
    "Los Angeles, USA":  {"tz": "America/Los_Angeles","lat": 34.0522,"lon": -118.2437,"fallback_offset": -8.0},
    "London, UK":        {"tz": "Europe/London",     "lat": 51.5074, "lon": -0.1278,  "fallback_offset": 0.0},
    "Paris, France":     {"tz": "Europe/Paris",      "lat": 48.8566, "lon": 2.3522,   "fallback_offset": 1.0},
    "Berlin, Germany":   {"tz": "Europe/Berlin",     "lat": 52.5200, "lon": 13.4050,  "fallback_offset": 1.0},
    "Sydney, Australia": {"tz": "Australia/Sydney",  "lat": -33.8688,"lon": 151.2093, "fallback_offset": 10.0},
    "Delhi, India":      {"tz": "Asia/Kolkata",      "lat": 28.6139, "lon": 77.2090,  "fallback_offset": 5.5},
    "Singapore":         {"tz": "Asia/Singapore",    "lat": 1.3521,  "lon": 103.8198, "fallback_offset": 8.0},
    "(手動入力)":          {"tz": None,                 "lat": None,    "lon": None,     "fallback_offset": 9.0},
}

# ---------- 便利関数 ----------
def map_gender_to_en(g: str) -> str:
    if g == "男性":
        return "male"
    if g == "女性":
        return "female"
    return "unknown"  # 不明・その他は unknown に統一

def get_offset_and_dst_label(tz_name: str, local_dt: datetime):
    """
    戻り値：
      offset_hours (float), is_dst (bool), label (str: 'UTC+9.0 (DST: No)' など)
    zoneinfo が無い場合は fallback（固定オフセット、DST判定は不可）
    """
    if tz_name and ZoneInfo is not None:
        try:
            aware = local_dt.replace(tzinfo=ZoneInfo(tz_name))
            offset_hours = aware.utcoffset().total_seconds() / 3600.0
            is_dst = (aware.dst() is not None) and (aware.dst() != timedelta(0))
            label = f"UTC{offset_hours:+.1f} (DST: {'Yes' if is_dst else 'No'})"
            return offset_hours, is_dst, label
        except Exception:
            pass  # 下のフォールバックへ

    # フォールバック：都市DBの固定オフセットを使用（DST判定なし）
    # tz_name から CITY_DB を逆引きできないので、別途呼び出し側で fallback を渡してもらうのが確実
    # ここでは便宜上、DST: Unknown とする
    # 実使用では呼び出し側で CITY_DB[item]["fallback_offset"] を使ってください
    return None, None, "UTC±?.? (DST: Unknown)"

def get_varga_data(jd, varga_factor, node_flag, lat, lon, compact=False):
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    planets["Rahu"] = swe.TRUE_NODE if "True" in node_flag else swe.MEAN_NODE

    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

    varga_res = {}

    # 各天体
    for name, pid in planets.items():
