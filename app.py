import streamlit as st
import swisseph as swe
import json
from datetime import date, time

st.set_page_config(page_title="AI Jyotish Data Generator", layout="centered")
st.title("🌌 AI専用ヴェーダ占星術データ抽出")

st.markdown("""
AIが正確に読み取れる形式でチャートを出力します。  
※緯度は **北緯(+) / 南緯(-)**、経度は **東経(+) / 西経(-)** で入力してください。
""")

# --- 入力フォーム ---
with st.expander("出生情報を入力", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # 日付：1900年から2100年まで選択可能に
        birth_date = st.date_input(
            "出生日", 
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date(2100, 12, 31)
        )
        # 緯度経度
        lat = st.number_input("緯度 (北緯は+, 南緯は-)", value=35.6895, format="%.4f")
        lon = st.number_input("経度 (東経は+, 西経は-)", value=139.6917, format="%.4f")

    with col2:
        # 時刻：時・分・秒を個別に数値入力
        st.write("出生時刻")
        c_h, c_m, c_s = st.columns(3)
        with c_h: h = st.number_input("時", 0, 23, 12)
        with c_m: m = st.number_input("分", 0, 59, 0)
        with c_s: s = st.number_input("秒", 0, 59, 0)
        
        # タイムゾーン
        tz = st.number_input("タイムゾーン (日本は 9.0)", value=9.0, step=0.5, format="%.1f")

# --- 計算ロジック ---
def get_varga_data(jd, varga_factor):
    # 計算対象の惑星（ラーフは平均値を使用）
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
        "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE
    }
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    varga_res = {}
    
    for name, id in planets.items():
        res, _ = swe.calc_ut(jd, id, swe.FLG_SIDEREAL)
        lon_val = res[0]
        # 分割図の計算
        v_lon = (lon_val * varga_factor) % 360
        v_sign_idx = int(v_lon / 30)
        varga_res[name] = {
            "Sign": signs[v_sign_idx],
            "Degree": f"{int(v_lon % 30)}° {int((v_lon * 60) % 60)}' {int((v_lon * 3600) % 60)}\""
        }
        
        # ケトゥの計算（ラーフの180度反対）
        if name == "Rahu":
            k_lon = (v_lon + 180) % 360
            varga_res["Ketu"] = {
                "Sign": signs[int(k_lon / 30)],
                "Degree": f"{int(k_lon % 30)}° {int((k_lon * 60) % 60)}' {int((k_lon * 3600) % 60)}\""
            }
            
    # ラグナ（Ascendant）の計算
    res, _ = swe.houses_ex(jd, lat, lon, b'P') # P = Placidus (Lagna自体は同じ)
    asc_lon = res[0]
    v_asc_lon = (asc_lon * varga_factor) % 360
    varga_res["Ascendant"] = {
        "Sign": signs[int(v_asc_lon / 30)],
        "Degree": f"{int(v_asc_lon % 30)}° {int((v_asc_lon * 60) % 60)}' {int((v_asc_lon * 3600) % 60)}\""
    }
    
    return varga_res

# --- 実行ボタン ---
if st.button("AI解析用データを生成", type="primary"):
    swe.set_sid_mode(swe.SIDM_LAHIRI) # ラヒリ・アイアナムシャ
    # 時刻をデシマル形式に変換 (秒まで考慮)
    hour_dec = h + (m / 60.0) + (s / 3600.0)
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_dec - tz)
    
    final_data = {
        "Metadata": {
            "Birth_Date": str(birth_date),
            "Birth_Time": f"{h:02d}:{m:02d}:{s:02d}",
            "Lat_Lon": f"{lat}, {lon}",
            "Ayanamsa": "Lahiri"
        },
        "D-1_Rashi": get_varga_data(jd, 1),
        "D-9_Navamsha": get_varga_data(jd, 9),
        "D-10_Dashamsha": get_varga_data(jd, 10),
        "D-60_Shashtiamsa": get_varga_data(jd, 60)
    }
    
    st.subheader("📋 このデータをコピーしてAIに渡してください")
    st.code(json.dumps(final_data, indent=4, ensure_ascii=False), language='json')
    st.balloons()
