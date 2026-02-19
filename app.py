import streamlit as st
import swisseph as swe
import json
from datetime import date, datetime, time, timezone, timedelta
from difflib import SequenceMatcher

# zoneinfo（標準）を優先。なければフォールバック（固定オフセットのみ）
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
# tz: IANA タイムゾーン名 / lat, lon: 緯度経度 / fallback_offset: 標準時のUTCオフセット（時間）
CITY_DB = {
    "Karuizawa, Japan":  {"tz": "Asia/Tokyo",        "lat": 36.3489, "lon": 138.6340, "fallback_offset": 9.0},
    "Tokyo, Japan":      {"tz": "Asia/Tokyo",        "lat": 35.6764, "lon": 139.6500, "fallback_offset": 9.0},
    "Osaka, Japan":      {"tz": "Asia/Tokyo",        "lat": 34.6937, "lon": 135.5023, "fallback_offset": 9.0},
    "Nagano, Japan":     {"tz": "Asia/Tokyo",        "lat": 36.6513, "lon": 138.1810, "fallback_offset": 9.0},
    "New York, USA":     {"tz": "America/New_York",  "lat": 40.7128, "lon": -74.0060,  "fallback_offset": -5.0},
    "Los Angeles, USA":  {"tz": "America/Los_Angeles","lat":34.0522, "lon": -118.2437, "fallback_offset": -8.0},
    "San Francisco, USA":{"tz": "America/Los_Angeles","lat":37.7749, "lon": -122.4194, "fallback_offset": -8.0},
    "London, UK":        {"tz": "Europe/London",     "lat": 51.5074, "lon": -0.1278,   "fallback_offset": 0.0},
    "Paris, France":     {"tz": "Europe/Paris",      "lat": 48.8566, "lon": 2.3522,    "fallback_offset": 1.0},
    "Berlin, Germany":   {"tz": "Europe/Berlin",     "lat": 52.5200, "lon": 13.4050,   "fallback_offset": 1.0},
    "Sydney, Australia": {"tz": "Australia/Sydney",  "lat": -33.8688,"lon": 151.2093,  "fallback_offset": 10.0},
    "Delhi, India":      {"tz": "Asia/Kolkata",      "lat": 28.6139, "lon": 77.2090,   "fallback_offset": 5.5},
    "Singapore":         {"tz": "Asia/Singapore",    "lat": 1.3521,  "lon": 103.8198,  "fallback_offset": 8.0},
    "(手動入力)":          {"tz": None,                 "lat": None,    "lon": None,      "fallback_offset": 9.0},
}

# ---------- 補助関数 ----------
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
    zoneinfo が無い場合は (None, None, 'UTC±?.? (DST: Unknown)') を返す
    """
    if tz_name and ZoneInfo is not None:
        try:
            aware = local_dt.replace(tzinfo=ZoneInfo(tz_name))
            offset_hours = aware.utcoffset().total_seconds() / 3600.0
            is_dst = (aware.dst() is not None) and (aware.dst() != timedelta(0))
            label = f"UTC{offset_hours:+.1f} (DST: {'Yes' if is_dst else 'No'})"
            return offset_hours, is_dst, label
        except Exception:
            pass
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
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        lon_val = res[0]
        v_lon = (lon_val * varga_factor) % 360
        s_idx = int(v_lon // 30)
        deg = round(v_lon % 30, 4)

        sign_out = SIG_ABBR[s_idx] if compact else signs[s_idx]
        key_out = PLANET_ABBR.get(name, name) if compact else name
        varga_res[key_out] = {"Sign": sign_out, "Degree": deg}

        if name == "Rahu":
            k_lon = (v_lon + 180) % 360
            k_idx = int(k_lon // 30)
            k_deg = round(k_lon % 30, 4)
            k_sign_out = SIG_ABBR[k_idx] if compact else signs[k_idx]
            k_key_out = PLANET_ABBR.get("Ketu", "Ketu") if compact else "Ketu"
            varga_res[k_key_out] = {"Sign": k_sign_out, "Degree": k_deg}

    # ラグナ
    res, _ = swe.houses_ex(jd, lat, lon, b'P')  # Placidus
    asc_lon = (res[0] * varga_factor) % 360
    a_idx = int(asc_lon // 30)
    a_deg = round(asc_lon % 30, 4)
    a_sign_out = SIG_ABBR[a_idx] if compact else signs[a_idx]
    a_key_out = PLANET_ABBR.get("Ascendant", "Ascendant") if compact else "Ascendant"
    varga_res[a_key_out] = {"Sign": a_sign_out, "Degree": a_deg}

    return varga_res

def to_json_str(obj, minify=True):
    if minify:
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    return json.dumps(obj, ensure_ascii=False, indent=2)

def search_cities(query: str, city_names, limit=30):
    """部分一致＋簡易ファジーマッチで候補を返す"""
    names = [n for n in city_names if n != "(手動入力)"]
    if not query:
        return sorted(names)[:limit] + ["(手動入力)"]
    q = query.strip().casefold()
    scored = []
    for name in names:
        ncf = name.casefold()
        score = 0.0
        if q in ncf:
            score += 2.0           # 部分一致を強く評価
        if ncf.startswith(q):
            score += 1.0           # 前方一致をやや優遇
        score += SequenceMatcher(None, q, ncf).ratio()  # 類似度
        scored.append((score, name))
    scored.sort(reverse=True)
    results = [name for _, name in scored[:limit]]
    results.append("(手動入力)")
    return results

# ---------- 1. 出生情報の入力 ----------
st.header("1. 出生情報の入力")

padL, main, padR = st.columns([1, 2, 1])
with main:
    with st.container(border=True):
        col_name, col_gen = st.columns([2, 1])
        with col_name:
            user_name = st.text_input("名前", value="Guest")
        with col_gen:
            gender = st.selectbox("性別（表示は日本語・出力は英語）",
                                  ["不明", "男性", "女性", "その他"])

        col_date, col_time_ui = st.columns(2)
        with col_date:
            birth_date = st.date_input(
                "出生日", value=date(1990, 1, 1), min_value=date(1900, 1, 1)
            )
        with col_time_ui:
            birth_time = st.time_input("出生時刻（24時間制）", value=time(12, 0), step=60)

        # --- 都市検索 + 選択 ---
        st.markdown("**出生地の都市を検索して選択**（ローマ字/英字・部分一致でOK）")
        if "selected_city" not in st.session_state:
            st.session_state.selected_city = "Karuizawa, Japan"
        if "city_query" not in st.session_state:
            st.session_state.city_query = ""

        city_query = st.text_input("都市検索", value=st.session_state.city_query, placeholder="例: Karuizawa / Tokyo / New York")
        st.session_state.city_query = city_query

        matches = search_cities(city_query, CITY_DB.keys(), limit=30)
        # 選択保持（フィルタ変更時にも選択が消えないように）
        idx_default = matches.index(st.session_state.selected_city) if st.session_state.selected_city in matches else 0
        city_choice = st.selectbox("都市を選択", matches, index=idx_default)
        st.session_state.selected_city = city_choice

        # 都市に応じて自動反映
        city_info = CITY_DB[city_choice]
        auto_lat = city_info["lat"]
        auto_lon = city_info["lon"]
        tz_name = city_info["tz"]

        local_dt = datetime.combine(birth_date, birth_time)
        off_hours, is_dst, label = get_offset_and_dst_label(tz_name, local_dt)
        if off_hours is None:
            off_hours = city_info["fallback_offset"]
            label = f"UTC{off_hours:+.1f} (DST: Unknown)"

        st.caption(f"タイムゾーン：{tz_name or '（手動）'} / 現地のUTCオフセット：{label}")

        # 緯度経度・UTCオフセットの手動編集
        manual_default = (city_choice == "(手動入力)")
        manual_geo = st.checkbox("緯度・経度・UTCオフセットを手動で編集する", value=manual_default)

        col_pos1, col_pos2, col_pos3 = st.columns(3)
        with col_pos1:
            lat = st.number_input("緯度 (北緯+, 南緯-)",
                                  value=float(auto_lat if auto_lat is not None else 35.0),
                                  format="%.4f", disabled=not manual_geo)
        with col_pos2:
            lon = st.number_input("経度 (東経+, 西経-)",
                                  value=float(auto_lon if auto_lon is not None else 135.0),
                                  format="%.4f", disabled=not manual_geo)
        with col_pos3:
            tz_offset_hours = st.number_input("UTCオフセット（時間, 例 +9.0）",
                                              value=float(off_hours if off_hours is not None else 9.0),
                                              step=0.5, format="%.1f", disabled=not manual_geo)

# ---------- 2. 出力方法の設定（クリックで開閉） ----------
with st.expander("2. 出力方法の設定（クリックで展開）", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        node_type = st.radio(
            "ノードの計算",
            ["Mean Node (平均)", "True Node (真位置)"],
            horizontal=True
        )
        use_compact_keys = st.checkbox("惑星キーとサイン名を短縮（例：Sun→Su, Aries→Ari）", value=True)
        minify_json = st.checkbox("JSONを最小化（スペース・改行なし）", value=True)
    with col_opt2:
        st.write("出力する分割図を選択")
        c_d1 = st.checkbox("D-1 (Rashi)", value=True)
        c_d9 = st.checkbox("D-9 (Navamsha)", value=True)
        c_d10 = st.checkbox("D-10 (Dashamsha)", value=True)
        c_d60 = st.checkbox("D-60 (Shashtiamsa)", value=True)

    custom_prompt = st.text_area(
        "AIへの追加指示",
        value="このチャートを元に、私の運命を詳しく分析してください。"
    )

# ---------- 実行 ----------
if st.button("AI解析用データを生成", type="primary"):
    # 恒星帯設定：Lahiri
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # 性別（英語化）
    gender_ai = map_gender_to_en(gender)

    # ローカル→UT の変換
    if (not manual_geo) and (tz_name is not None) and (ZoneInfo is not None):
        # 都市選択 & zoneinfo 利用可：DST を含む正確な UTC 時刻へ
        aware_local = datetime.combine(birth_date, birth_time, tzinfo=ZoneInfo(tz_name))
        aware_utc = aware_local.astimezone(timezone.utc)
        ut_hour_dec = aware_utc.hour + aware_utc.minute/60.0 + aware_utc.second/3600.0
        jd = swe.julday(aware_utc.year, aware_utc.month, aware_utc.day, ut_hour_dec)
        tz_info_for_output = {
            "IANA_TZ": tz_name,
            "UTC_Offset_at_birth": round((aware_local.utcoffset().total_seconds()/3600.0), 1),
            "DST_in_effect": bool((aware_local.dst() or timedelta(0)) != timedelta(0))
        }
    else:
        # フォールバック：固定オフセットで UT 化（DSTは考慮しない）
        hour_dec_local = birth_time.hour + birth_time.minute/60.0 + birth_time.second/3600.0
        ut_hour_dec = hour_dec_local - tz_offset_hours
        jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, ut_hour_dec)
        tz_info_for_output = {
            "IANA_TZ": tz_name or None,
            "UTC_Offset_at_birth": round(tz_offset_hours, 1),
            "DST_in_effect": None  # Unknown
        }

    # 分割図の作成
    selected_charts = {}
    if c_d1:
        selected_charts["D-1_Rashi"] = get_varga_data(jd, 1, node_type, lat, lon, compact=use_compact_keys)
    if c_d9:
        selected_charts["D-9_Navamsha"] = get_varga_data(jd, 9, node_type, lat, lon, compact=use_compact_keys)
    if c_d10:
        selected_charts["D-10_Dashamsha"] = get_varga_data(jd, 10, node_type, lat, lon, compact=use_compact_keys)
    if c_d60:
        selected_charts["D-60_Shashtiamsa"] = get_varga_data(jd, 60, node_type, lat, lon, compact=use_compact_keys)

    # 出力オブジェクト
    final_output = {
        "User_Profile": {
            "Name": user_name,
            "Gender": gender_ai,  # male / female / unknown
            "Birth": f"{birth_date} {birth_time.strftime('%H:%M:%S')}",
            "Location": {"Lat": round(float(lat), 4), "Lon": round(float(lon), 4)},
            "Settings": {
                "Node": node_type,
                "Ayanamsa": "Lahiri",
                **tz_info_for_output
            }
        },
        "Instructions": custom_prompt,
        "Charts": selected_charts
    }

    # JSON 表示 & ダウンロード
    json_str = to_json_str(final_output, minify=minify_json)

    st.divider()
    st.code(json_str, language='json')

    file_base = f"jyotish_{birth_date.isoformat()}_{birth_time.strftime('%H%M%S')}.json"
    st.download_button(
        label="JSONをダウンロード",
        data=json_str.encode("utf-8"),
        file_name=file_base,
        mime="application/json"
    )

    st.success("上のJSONをコピー、または『JSONをダウンロード』から取得してください。")
