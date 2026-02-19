import streamlit as st
import swisseph as swe
import json
from datetime import date, time

st.set_page_config(page_title="AI Jyotish Data Generator", layout="wide")
st.title("🌌 AI専用ヴェーダ占星術データ抽出")

# --- 入力フォーム ---
with st.container():
    st.subheader("👤 出生情報の入力")
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        user_name = st.text_input("名前", value="Guest")
        gender = st.selectbox("性別", ["不明", "男性", "女性", "その他"])
        node_type = st.radio("ノード (Rahu/Ketu) の計算", ["Mean (平均値)", "True (真位置)"])

    with col_b:
        # 日付入力：カレンダーでも手打ちでも可能
        birth_date = st.date_input(
            "出生日", 
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date(2100, 12, 31)
        )
        # 時刻入力：マウス選択・手打ち両対応
        birth_time = st.time_input("出生時刻 (秒まで入力・選択可)", value=time(12, 0, 0), step=1)
        tz = st.number_input("タイムゾーン (日本は 9.0)", value=9.0, step=0.5, format="%.1f")

    with col_c:
        lat = st.number_input("緯度 (北緯+, 南緯-)", value=35.6895, format="%.4f", help="東京: 35.6895")
        lon = st.number_input("経度 (東経+, 西経-)", value=139.6917, format="%.4f", help="東京: 139.6917")

# --- AIへの指示（プロンプトテンプレート） ---
st.subheader("🤖 AIへの出力指示")
custom_prompt = st.text_area("AIに渡す追加の指示があれば入力してください", 
    value="このチャートを元に、私の基本的な性格と、特に仕事運（D-10）について詳しく分析してください。",
    height=100)

# --- 計算ロジック ---
def get_varga_data(jd, varga_factor, node_flag):
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    # ノードの設定
    planets["Rahu"] = swe.TRUE_NODE if "True" in node_flag else swe.MEAN_NODE
    
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    varga_res = {}
    
    for name, id in planets.items():
        res, _ = swe.calc_ut(jd, id, swe.FLG_SIDEREAL)
        lon_val = res[0]
        v_lon = (lon_val * varga_factor) % 360
        v_sign_idx = int(v_lon / 30)
        
        # AIが計算しやすい小数点表示をメインにし、補足として度分秒を付ける
        d = int(v_lon % 30)
        m = int((v_lon * 60) % 60)
        s = int((v_lon * 3600) % 60)
        
        varga_res[name] = {
            "Sign": signs[v_sign_idx],
            "Degree_Decimal": round(v_lon % 30, 4),
            "DMS": f"{d}°{m}'{s}\""
        }
        
        if name == "Rahu":
            k_lon = (v_lon + 180) % 360
            varga_res["Ketu"] = {
                "Sign": signs[int(k_lon / 30)],
                "Degree_Decimal": round(k_lon % 30, 4),
                "DMS": f"{int(k_lon % 30)}°{int((k_lon * 60) % 60)}'{int((k_lon * 3600) % 60)}\""
            }
            
    # ラグナ（Ascendant）
    res, _ = swe.houses_ex(jd, lat, lon, b'P')
    asc_lon = res[0]
    v_asc_lon = (asc_lon * varga_factor) % 360
    varga_res["Ascendant"] = {
        "Sign": signs[int(v_asc_lon / 30)],
        "Degree_Decimal": round(v_asc_lon % 30, 4),
        "DMS": f"{int(v_asc_lon % 30)}°{int((v_asc_lon * 60) % 60)}'{int((v_asc_lon * 3600) % 60)}\""
    }
    
    return varga_res

# --- 実行ボタン ---
if st.button("AI解析用データを生成", type="primary"):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    hour_dec = birth_time.hour + (birth_time.minute / 60.0) + (birth_time.second / 3600.0)
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_dec - tz)
    
    final_output = {
        "User_Profile": {
            "Name": user_name,
            "Gender": gender,
            "Birth_Date": str(birth_date),
            "Birth_Time": str(birth_time),
            "Location": {"Lat": lat, "Lon": lon, "TZ": tz},
            "Settings": {"Ayanamsa": "Lahiri", "Node": node_type}
        },
        "Instructions": custom_prompt,
        "Charts": {
            "D-1_Rashi": get_varga_data(jd, 1, node_type),
            "D-9_Navamsha": get_varga_data(jd, 9, node_type),
            "D-10_Dashamsha": get_varga_data(jd, 10, node_type),
            "D-60_Shashtiamsa": get_varga_data(jd, 60, node_type)
        }
    }
    
    st.divider()
    st.subheader("📋 AIにコピー＆ペーストする内容")
    st.info("下の枠内のテキストをすべてコピーして、ChatGPTやClaudeに貼り付けてください。")
    st.code(json.dumps(final_output, indent=4, ensure_ascii=False), language='json')
    st.balloons()
