import streamlit as st
import swisseph as swe
import json
from datetime import date

# ------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------
st.set_page_config(page_title="AI Jyotish Data Generator", layout="wide")
st.title("🌌 AI専用ヴェーダ占星術データ抽出")

# 惑星キー短縮・サイン略号
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

def node_flag_str(is_true_node: bool) -> str:
    """calc 用フラグ文字列（内部判定に使用）"""
    return "True" if is_true_node else "Mean"

# ------------------------------------------------------------
# Varga 計算
# ------------------------------------------------------------
def get_varga_data(jd, varga_factor, is_true_node, lat, lon, compact=False):
    # 惑星セット
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    planets["Rahu"] = swe.TRUE_NODE if is_true_node else swe.MEAN_NODE

    # サイン
    signs = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    out = {}

    # 各天体
    for name, pid in planets.items():
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        lon_val = res[0]
        vlon = (lon_val * varga_factor) % 360
        sidx = int(vlon // 30)
        deg  = round(vlon % 30, 4)

        sign_out = SIG_ABBR[sidx] if compact else signs[sidx]
        key_out  = PLANET_ABBR.get(name, name) if compact else name

        out[key_out] = {"Sign": sign_out, "Degree": deg}

        if name == "Rahu":
            # Ketu は対向
            klon = (vlon + 180) % 360
            ksidx = int(klon // 30)
            kdeg  = round(klon % 30, 4)
            ksign = SIG_ABBR[ksidx] if compact else signs[ksidx]
            kkey  = PLANET_ABBR.get("Ketu","Ketu") if compact else "Ketu"
            out[kkey] = {"Sign": ksign, "Degree": kdeg}

    # Ascendant
    res2, _ = swe.houses_ex(jd, lat, lon, b'P')  # Placidus
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
# 1. 出生情報の入力（コンパクトな一行レイアウト）
# ------------------------------------------------------------
st.header("1. 出生情報の入力")

with st.container(border=True):

    # 名前・性別
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1:
        user_name = st.text_input("名前", value="Guest")
    with c2:
        gender = st.selectbox("性別（表示は日本語・出力は英語）",
                              ["不明","男性","女性","その他"])

    # 出生日＋時刻（1行）
    st.write("出生日・時刻")
    d1, d2, d3, d4 = st.columns([1.8, 1, 1, 1])
    with d1:
        birth_date = st.date_input("出生日", value=date(1990,1,1),
                                   min_value=date(1900,1,1))
    with d2:
        h = st.selectbox("時", list(range(0,24)), index=12)
    with d3:
        m = st.selectbox("分", list(range(0,60)), index=0)
    with d4:
        s = st.selectbox("秒", list(range(0,60)), index=0)

    # 緯度・経度・UTC offset（1行）
    st.write("出生地（緯度・経度・UTCオフセット）")
    g1, g2, g3 = st.columns([1, 1, 1])
    with g1:
        lat = st.number_input("緯度（北緯+／南緯-）", value=35.000000, format="%.6f")
    with g2:
        lon = st.number_input("経度（東経+／西経-）", value=135.000000, format="%.6f")
    with g3:
        tz = st.number_input("UTCオフセット", value=9.0, step=0.5, format="%.1f")

# ------------------------------------------------------------
# 2. 出力方法の設定（拡充した分割図）
# ------------------------------------------------------------
st.header("2. 出力方法の設定")
with st.expander("クリックで展開", expanded=False):

    col_op1, col_op2 = st.columns(2)

    with col_op1:
        # UIの表示は日本語を含むが、出力JSONでは英語の "Mean"/"True" のみを使う
        node_ui = st.radio("ノードの計算",
                           ["Mean Node (平均)", "True Node (真位置)"],
                           horizontal=True)
        is_true_node = (node_ui.startswith("True"))
        use_compact = st.checkbox("惑星キー・サイン名を短縮（Sun→Su, Aries→Ari）", value=True)
        minify_json = st.checkbox("JSONを最小化（スペース・改行なし）", value=True)

    with col_op2:
        st.write("出力する分割図（複数選択）")
        # D1, D9 は従来通り。以下、ご要望の分割図を追加
        d1  = st.checkbox("D1 Rashi（基本）", value=True)
        d9  = st.checkbox("D9 Navamsa（配偶者・ダルマ）", value=True)
        d3  = st.checkbox("D3 Drekkana（兄弟姉妹）", value=False)
        d4  = st.checkbox("D4 Chaturthamsa（住居・運）", value=False)
        d7  = st.checkbox("D7 Saptamsa（子供・孫）", value=False)
        d10 = st.checkbox("D10 Dasamsa（職業・達成）", value=False)
        d12 = st.checkbox("D12 Dwadasamsa（両親）", value=False)
        d16 = st.checkbox("D16 Shodasamsa（乗り物）", value=False)
        d20 = st.checkbox("D20 Vimsamsa（霊性・宗教性）", value=False)
        d24 = st.checkbox("D24 Chaturvimsamsa（教育・知識）", value=False)
        d30 = st.checkbox("D30 Trimsamsa（困難・試練）", value=False)
        d60 = st.checkbox("D60 Shashtyamsa", value=False)

    custom_prompt = st.text_area(
        "AIへの追加指示",
        value="このチャートを元に、私の運命を詳しく分析してください。"
    )

# ------------------------------------------------------------
# 実行
# ------------------------------------------------------------
if st.button("AI解析用データを生成", type="primary"):

    # 恒星帯設定：Lahiri
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # 性別（英語）
    gender_ai = map_gender_to_en(gender)

    # ローカル時刻 → UT
    hour_local = h + m/60 + s/3600
    hour_utc   = hour_local - tz
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_utc)

    # 選択チャート計算
    charts = {}
    if d1:  charts["D1_Rashi"]          = get_varga_data(jd, 1,  is_true_node, lat, lon, compact=use_compact)
    if d9:  charts["D9_Navamsa"]        = get_varga_data(jd, 9,  is_true_node, lat, lon, compact=use_compact)
    if d3:  charts["D3_Drekkana"]       = get_varga_data(jd, 3,  is_true_node, lat, lon, compact=use_compact)
    if d4:  charts["D4_Chaturthamsa"]   = get_varga_data(jd, 4,  is_true_node, lat, lon, compact=use_compact)
    if d7:  charts["D7_Saptamsa"]       = get_varga_data(jd, 7,  is_true_node, lat, lon, compact=use_compact)
    if d10: charts["D10_Dasamsa"]       = get_varga_data(jd, 10, is_true_node, lat, lon, compact=use_compact)
    if d12: charts["D12_Dwadasamsa"]    = get_varga_data(jd, 12, is_true_node, lat, lon, compact=use_compact)
    if d16: charts["D16_Shodasamsa"]    = get_varga_data(jd, 16, is_true_node, lat, lon, compact=use_compact)
    if d20: charts["D20_Vimsamsa"]      = get_varga_data(jd, 20, is_true_node, lat, lon, compact=use_compact)
    if d24: charts["D24_Chaturvimsamsa"]= get_varga_data(jd, 24, is_true_node, lat, lon, compact=use_compact)
    if d30: charts["D30_Trimsamsa"]     = get_varga_data(jd, 30, is_true_node, lat, lon, compact=use_compact)
    if d60: charts["D60_Shashtyamsa"]   = get_varga_data(jd, 60, is_true_node, lat, lon, compact=use_compact)

    # Node は UI と独立して、英語のみをJSONに出力
    node_value_for_json = "True" if is_true_node else "Mean"

    final_output = {
        "User_Profile": {
            "Name": user_name,
            "Gender": gender_ai,
            "Birth": f"{birth_date} {h:02d}:{m:02d}:{s:02d}",
            "Location": {"Lat": lat, "Lon": lon},
            "Settings": {
                "Node": node_value_for_json,   # ← 日本語を含めない
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
