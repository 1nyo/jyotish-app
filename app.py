import streamlit as st
import swisseph as swe
import json

st.set_page_config(page_title="AI Jyotish Data Generator", layout="centered")
st.title("🌌 AI専用ヴェーダ占星術データ生成")
st.write("出生情報を入力すると、AIが解析しやすい形式でデータを出力します。")

# --- サイドバー：入力フォーム ---
with st.sidebar:
    st.header("出生データ入力")
    date = st.date_input("出生日", value=None)
    time = st.time_input("出生時間", value=None)
    lat = st.number_input("緯度 (例: 東京 35.68)", value=35.68)
    lon = st.number_input("経度 (例: 東京 139.69)", value=139.69)
    tz = st.number_input("タイムゾーン (日本は 9.0)", value=9.0)

# --- 計算ロジック ---
def get_varga_data(jd, varga_factor):
    planets = {"Sun": 0, "Moon": 1, "Mars": 4, "Mercury": 2, "Jupiter": 5, "Venus": 3, "Saturn": 6, "Rahu": 10}
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    varga_res = {}
    
    for name, id in planets.items():
        res, _ = swe.calc_ut(jd, id, swe.FLG_SIDEREAL)
        lon_val = res[0]
        v_lon = (lon_val * varga_factor) % 360
        varga_res[name] = {
            "Sign": signs[int(v_lon / 30)],
            "Degree": f"{round(v_lon % 30, 2)}°"
        }
    return varga_res

# --- 実行ボタン ---
if st.button("AI用データを生成する"):
    if date and time:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        hour_dec = time.hour + time.minute / 60.0
        jd = swe.julday(date.year, date.month, date.day, hour_dec - tz)
        
        # 各チャートの計算
        final_data = {
            "D-1_Rashi": get_varga_data(jd, 1),
            "D-9_Navamsha": get_varga_data(jd, 9),
            "D-10_Dashamsha": get_varga_data(jd, 10)
        }
        
        # 出力
        st.subheader("📋 AIにコピー＆ペーストしてください")
        st.code(json.dumps(final_data, indent=4, ensure_ascii=False), language='json')
        st.success("このデータをChatGPTやClaudeに渡して、「このチャートを分析して」と指示してください。")
    else:
        st.warning("日付と時間を入力してください。")
