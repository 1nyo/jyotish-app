import streamlit as st
import swisseph as swe
import json
from datetime import date

st.set_page_config(page_title="AI Jyotish Data Generator", layout="wide")
st.title("🌌 AI専用ヴェーダ占星術データ抽出")

# --- 1. 出生情報の入力 ---
st.header("1. 出生情報の入力")
with st.container(border=True):
    col_name, col_gen = st.columns(2)
    with col_name:
        user_name = st.text_input("名前", value="Guest")
    with col_gen:
        gender = st.selectbox("性別", ["不明", "男性", "女性", "その他"])

    col_date, col_time = st.columns(2)
    with col_date:
        birth_date = st.date_input("出生日", value=date(1990, 1, 1), min_value=date(1900, 1, 1))
    with col_time:
        st.write("出生時刻 (24時間制)")
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1: h = st.number_input("時", 0, 23, 12)
        with t_col2: m = st.number_input("分", 0, 59, 0)
        with t_col3: s = st.number_input("秒", 0, 59, 0)

    col_pos1, col_pos2, col_pos3 = st.columns(3)
    with col_pos1:
        lat = st.number_input("緯度 (北緯+, 南緯-)", value=35.6895, format="%.4f")
    with col_pos2:
        lon = st.number_input("経度 (東経+, 西経-)", value=139.6917, format="%.4f")
    with col_pos3:
        tz = st.number_input("タイムゾーン", value=9.0, step=0.5)

# --- 2. 出力方法の設定 ---
st.header("2. 出力方法の設定")
with st.container(border=True):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        node_type = st.radio("ノードの計算", ["Mean Node (平均)", "True Node (真位置)"], horizontal=True)
    with col_opt2:
        st.write("出力する分割図を選択")
        c_d1 = st.checkbox("D-1 (Rashi)", value=True)
        c_d9 = st.checkbox("D-9 (Navamsha)", value=True)
        c_d10 = st.checkbox("D-10 (Dashamsha)", value=True)
        c_d60 = st.checkbox("D-60 (Shashtiamsa)", value=True)

    custom_prompt = st.text_area("AIへの追加指示", value="このチャートを元に、私の運命を詳しく分析してください。")

# --- 計算ロジック ---
def get_varga_data(jd, varga_factor, node_flag, lat, lon):
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    planets["Rahu"] = swe.TRUE_NODE if "True" in node_flag else swe.MEAN_NODE
    
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    varga_res = {}
    
    # 各天体の計算
    for name, id in planets.items():
        res, _ = swe.calc_ut(jd, id, swe.FLG_SIDEREAL)
        lon_val = res[0]
        v_lon = (lon_val * varga_factor) % 360
        varga_res[name] = {
            "Sign": signs[int(v_lon / 30)],
            "Degree": round(v_lon % 30, 4)
        }
        if name == "Rahu":
            k_lon = (v_lon + 180) % 360
            varga_res["Ketu"] = {"Sign": signs[int(k_lon / 30)], "Degree": round(k_lon % 30, 4)}
            
    # ラグナの計算
    res, _ = swe.houses_ex(jd, lat, lon, b'P')
    asc_lon = (res[0] * varga_factor) % 360
    varga_res["Ascendant"] = {"Sign": signs[int(asc_lon / 30)], "Degree": round(asc_lon % 30, 4)}
    
    return varga_res

# --- 実行 ---
if st.button("AI解析用データを生成", type="primary"):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    hour_dec = h + (m / 60.0) + (s / 3600.0)
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_dec - tz)
    
    selected_charts = {}
    if c_d1: selected_charts["D-1_Rashi"] = get_varga_data(jd, 1, node_type, lat, lon)
    if c_d9: selected_charts["D-9_Navamsha"] = get_varga_data(jd, 9, node_type, lat, lon)
    if c_d10: selected_charts["D-10_Dashamsha"] = get_varga_data(jd, 10, node_type, lat, lon)
    if c_d60: selected_charts["D-60_Shashtiamsa"] = get_varga_data(jd, 60, node_type, lat, lon)
    
    final_output = {
        "User_Profile": {
            "Name": user_name, "Gender": gender,
            "Birth": f"{birth_date} {h:02d}:{m:02d}:{s:02d}",
            "Settings": {"Node": node_type, "Ayanamsa": "Lahiri"}
        },
        "Instructions": custom_prompt,
        "Charts": selected_charts
    }
    
    st.divider()
    st.code(json.dumps(final_output, indent=4, ensure_ascii=False), language='json')
    st.success("上のデータをコピーしてAIに貼り付けてください。")
