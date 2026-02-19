import streamlit as st
import swisseph as swe
import json
from datetime import date, datetime, timezone, timedelta

# ------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------
st.set_page_config(page_title="AI Jyotish Data Generator", layout="wide")
st.title("🌌 AI専用ヴェーダ占星術データ抽出")

PLANET_ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
    "Rahu": "Ra", "Ketu": "Ke", "Ascendant": "Asc"
}

SIG_ABBR = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]

def map_gender_to_en(g):
    if g == "男性":
        return "male"
    if g == "女性":
        return "female"
    return "unknown"

# ------------------------------------------------------------
# Varga 計算部分
# ------------------------------------------------------------
def get_varga_data(jd, varga_factor, node_flag, lat, lon, compact=False):
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    planets["Rahu"] = swe.TRUE_NODE if "True" in node_flag else swe.MEAN_NODE

    signs = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    out = {}

    for name, pid in planets.items():
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        lon_val = res[0]
        vlon = (lon_val * varga_factor) % 360
        sidx = int(vlon // 30)
        deg  = round(vlon % 30, 4)

        sign_out = SIG_ABBR[sidx] if compact else signs[sidx]
        key_out  = PLANET_ABBR.get(name,name) if compact else name

        out[key_out] = {"Sign": sign_out, "Degree": deg}

        # Ketu
        if name == "Rahu":
            klon = (vlon + 180) % 360
            ksidx = int(klon // 30)
            kdeg  = round(klon % 30, 4)
            ksign = SIG_ABBR[ksidx] if compact else signs[ksidx]
            kkey  = PLANET_ABBR.get("Ketu","Ketu") if compact else "Ketu"
            out[kkey] = {"Sign": ksign, "Degree": kdeg}

    # Ascendant
    res2, _ = swe.houses_ex(jd, lat, lon, b'P')
    asc_lon = (res2[0] * varga_factor) % 360
    aidx = int(asc_lon // 30)
    adeg = round(asc_lon % 30, 4)
    asign = SIG_ABBR[aidx] if compact else signs[aidx]
    akey = PLANET_ABBR.get("Ascendant","Ascendant") if compact else "Ascendant"
    out[akey] = {"Sign": asign, "Degree": adeg}

    return out


def to_json(obj, minify=True):
    if minify:
        return json.dumps(obj, ensure_ascii=False, separators=(",",":"))
    return json.dumps(obj, ensure_ascii=False, indent=2)

# ------------------------------------------------------------
# 1. 出生情報入力
# ------------------------------------------------------------
st.header("1. 出生情報の入力")

with st.container(border=True):

    col_name, col_gen = st.columns(2)
    with col_name:
        user_name = st.text_input("名前", value="Guest")
    with col_gen:
        gender = st.selectbox("性別（表示は日本語・出力は英語）",
                              ["不明","男性","女性","その他"])

    birth_date = st.date_input("出生日", value=date(1990,1,1),
                               min_value=date(1900,1,1))

    st.write("出生時刻（ドロップダウン）")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        h = st.selectbox("時", list(range(0,24)), index=12)
    with col_m:
        m = st.selectbox("分", list(range(0,60)), index=0)
    with col_s:
        s = st.selectbox("秒", list(range(0,60)), index=0)

    st.write("出生地（緯度・経度手入力）")
    col_lat, col_lon = st.columns(2)
    with col_lat:
        lat = st.number_input("緯度（北緯+ / 南緯-）", value=35.000000, format="%.6f")
    with col_lon:
        lon = st.number_input("経度（東経+ / 西経-）", value=135.000000, format="%.6f")

    tz = st.number_input("UTCオフセット（例：日本=+9.0）", 
                         value=9.0, step=0.5, format="%.1f")

# ------------------------------------------------------------
# 2. 出力方法の設定
# ------------------------------------------------------------
st.header("2. 出力方法の設定")
with st.expander("クリックで展開", expanded=False):

    col_op1, col_op2 = st.columns(2)

    with col_op1:
        node_type = st.radio(
            "ノードの計算",
            ["Mean Node (平均)", "True Node (真位置)"],
            horizontal=True
        )
        use_compact = st.checkbox("惑星キー・サイン名を短縮（Sun→Su, Aries→Ari）", value=True)
        minify_json = st.checkbox("JSONを最小化（スペース・改行なし）", value=True)

    with col_op2:
        st.write("出力する分割図（複数選択）")
        c1 = st.checkbox("D-1 (Rashi)", value=True)
        c9 = st.checkbox("D-9 (Navamsha)", value=True)
        c10 = st.checkbox("D-10 (Dashamsha)", value=True)
        c60 = st.checkbox("D-60 (Shashtiamsa)", value=True)

    custom_prompt = st.text_area(
        "AIへの追加指示",
        value="このチャートを元に、私の運命を詳しく分析してください。"
    )

# ------------------------------------------------------------
# 実行
# ------------------------------------------------------------
if st.button("AI解析用データを生成", type="primary"):

    swe.set_sid_mode(swe.SIDM_LAHIRI)

    gender_ai = map_gender_to_en(gender)

    # ローカル時刻 → UT
    hour_dec_local = h + m/60 + s/3600
    hour_dec_utc   = hour_dec_local - tz
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_dec_utc)

    charts = {}
    if c1:
        charts["D-1_Rashi"] = get_varga_data(jd,1,node_type,lat,lon,compact=use_compact)
    if c9:
        charts["D-9_Navamsha"] = get_varga_data(jd,9,node_type,lat,lon,compact=use_compact)
    if c10:
        charts["D-10_Dashamsha"] = get_varga_data(jd,10,node_type,lat,lon,compact=use_compact)
    if c60:
        charts["D-60_Shashtiamsa"] = get_varga_data(jd,60,node_type,lat,lon,compact=use_compact)

    final_output = {
        "User_Profile": {
            "Name": user_name,
            "Gender": gender_ai,
            "Birth": f"{birth_date} {h:02d}:{m:02d}:{s:02d}",
            "Location": {"Lat": lat, "Lon": lon},
            "Settings": {
                "Node": node_type,
                "Ayanamsa": "Lahiri",
                "UTC_Offset": tz
            },
        },
        "Instructions": custom_prompt,
        "Charts": charts
    }

    json_str = to_json(final_output, minify=minify_json)

    st.divider()
    st.code(json_str, language="json")

    filename = f"jyotish_{birth_date.isoformat()}_{h:02d}{m:02d}{s:02d}.json"
    st.download_button(
        label="JSONをダウンロード",
        data=json_str.encode("utf-8"),
        file_name=filename,
        mime="application/json",
    )

    st.success("JSONをコピーするか、ダウンロードしてください。")
