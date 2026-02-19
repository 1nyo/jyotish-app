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

# 27 Nakshatras（0°Aries=Ashwini）
NAK_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha",
    "Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# 短縮表記（例に合わせて "Sata" / "UBha" を採用）
NAK_ABBR = {
    "Ashwini":"Ashw","Bharani":"Bhar","Krittika":"Krit","Rohini":"Rohi","Mrigashira":"Mri",
    "Ardra":"Ardr","Punarvasu":"Puna","Pushya":"Push","Ashlesha":"Ashl","Magha":"Magh",
    "Purva Phalguni":"PPhal","Uttara Phalguni":"UPhal","Hasta":"Hast","Chitra":"Chit","Swati":"Swat",
    "Vishakha":"Vish","Anuradha":"Anur","Jyeshtha":"Jyes","Mula":"Mula","Purva Ashadha":"PAsh",
    "Uttara Ashadha":"UAsh","Shravana":"Shra","Dhanishta":"Dhan","Shatabhisha":"Sata",
    "Purva Bhadrapada":"PBha","Uttara Bhadrapada":"UBha","Revati":"Reva"
}

def map_gender_to_en(g):
    if g == "男性":
        return "male"
    if g == "女性":
        return "female"
    return "unknown"

# ---- ナクシャトラ算出（名前・Pada） ----
def compute_nakshatra(lon_deg: float):
    """
    lon_deg: 恒星帯の黄経（度, 0-360）
    返り値: (nak_name, pada[1..4])
    """
    lon = lon_deg % 360.0
    unit = 360.0 / 27.0  # 13.3333...°
    idx = int(lon // unit)  # 0..26
    pada = int(((lon % unit) // (unit / 4.0))) + 1  # 1..4
    return NAK_NAMES[idx], pada

def format_nak_abbr(nak_name: str, pada: int) -> str:
    """短縮 'nak' 形式（例：'Sata-3' / 'UBha-3'）"""
    abbr = NAK_ABBR.get(nak_name, nak_name[:4])
    return f"{abbr}-{pada}"

# ------------------------------------------------------------
# Varga 計算
#   - 角度は小数点2桁
#   - Asc を先頭に出力（asc_first=True）
#   - D1 のみ：速度（Speed, deg/day）とナクシャトラ（形式トグル）を付与
#   - ★ 速度を取得するため calc_ut のフラグに FLG_SPEED を付与
# ------------------------------------------------------------
def get_varga_data(
    jd, varga_factor, is_true_node, lat, lon,
    compact_planet=False, short_sd_keys=False,
    include_speed=False, include_nakshatra=False,
    nak_single=False,   # True: 'nak' フィールド（短縮＋pada連結）
    asc_first=True
):
    """
    compact_planet=True  -> 惑星キー短縮（Sun->Su）＆サイン3文字（Ari...）
    short_sd_keys=True   -> 'Sign','Degree' を 'sg','deg' に短縮
    include_speed        -> 速度を出力（deg/day, D1 用）
    include_nakshatra    -> ナクシャトラ名・Pada を出力（D1 用）
    nak_single           -> 'nak' フィールド（短縮＋pada連結）で出力
    asc_first            -> Asc を先頭に出力
    """
    key_sign = "sg" if short_sd_keys else "Sign"
    key_deg  = "deg" if short_sd_keys else "Degree"

    signs = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    out = {}

    # ---- Ascendant（先頭出力のため先に計算）----
    res_asc, _ = swe.houses_ex(jd, lat, lon, b'P')  # Placidus
    asc_lon_sid = res_asc[0] % 360.0
    asc_vlon    = (asc_lon_sid * varga_factor) % 360.0
    aidx = int(asc_vlon // 30.0)
    adeg = round(asc_vlon % 30.0, 2)
    asign = SIG_ABBR[aidx] if compact_planet else signs[aidx]
    akey  = PLANET_ABBR.get("Ascendant","Ascendant") if compact_planet else "Ascendant"

    asc_obj = {key_sign: asign, key_deg: adeg}
    if include_nakshatra:
        nk_name_a, nk_pada_a = compute_nakshatra(asc_lon_sid)
        if nak_single:
            asc_obj["nak"] = format_nak_abbr(nk_name_a, nk_pada_a)
        else:
            asc_obj["Nakshatra"] = nk_name_a
            asc_obj["Pada"] = nk_pada_a

    if asc_first:
        out[akey] = asc_obj  # 先頭

    # ---- 惑星セット ----
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    planets["Rahu"] = swe.TRUE_NODE if is_true_node else swe.MEAN_NODE

    # ★ 速度を得るための flags
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    # ---- 各天体 ----
    for name, pid in planets.items():
        res, _ = swe.calc_ut(jd, pid, flags)
        lon_sid = res[0] % 360.0     # D1 恒星黄経（nak 算出基準）
        spd     = res[3]             # ★ deg/day（丸めなし）

        vlon = (lon_sid * varga_factor) % 360.0
        sidx = int(vlon // 30.0)
        deg  = round(vlon % 30.0, 2)

        sign_out = SIG_ABBR[sidx] if compact_planet else signs[sidx]
        key_out  = PLANET_ABBR.get(name, name) if compact_planet else name

        base = {key_sign: sign_out, key_deg: deg}

        if include_speed:
            # ★ 丸め禁止：そのまま出力（JSONの浮動小数表現に委ねる）
            base["Speed"] = spd

        if include_nakshatra:
            nk_name, nk_pada = compute_nakshatra(lon_sid)
            if nak_single:
                base["nak"] = format_nak_abbr(nk_name, nk_pada)
            else:
                base["Nakshatra"] = nk_name
                base["Pada"] = nk_pada

        out[key_out] = base

        # ---- Ketu（Rahu と対向）----
        if name == "Rahu":
            k_lon_sid = (lon_sid + 180.0) % 360.0
            k_vlon    = (vlon + 180.0) % 360.0
            ksidx     = int(k_vlon // 30.0)
            kdeg      = round(k_vlon % 30.0, 2)
            ksign     = SIG_ABBR[ksidx] if compact_planet else signs[ksidx]
            kkey      = PLANET_ABBR.get("Ketu","Ketu") if compact_planet else "Ketu"

            base_k = {key_sign: ksign, key_deg: kdeg}
            if include_speed:
                base_k["Speed"] = None  # Ketu の速度は None（モデル化しない）

            if include_nakshatra:
                nk_name_k, nk_pada_k = compute_nakshatra(k_lon_sid)
                if nak_single:
                    base_k["nak"] = format_nak_abbr(nk_name_k, nk_pada_k)
                else:
                    base_k["Nakshatra"] = nk_name_k
                    base_k["Pada"] = nk_pada_k

            out[kkey] = base_k

    return out

def to_json(obj, minify=True):
    if minify:
        return json.dumps(obj, ensure_ascii=False, separators=(",",":"))
    return json.dumps(obj, ensure_ascii=False, indent=2)

# ------------------------------------------------------------
# 1. 出生情報の入力（コンパクト一行レイアウト）
# ------------------------------------------------------------
st.header("1. 出生情報の入力")

with st.container(border=True):

    # 名前・性別
    c1, c2, _ = st.columns([2, 1.5, 0.5])
    with c1:
        user_name = st.text_input("名前", value="Guest")
    with c2:
        gender = st.selectbox("性別", ["不明","男性","女性","その他"])

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
# 2. 出力方法の設定（順序：D1, D9, D3, D4, D7, D10, D12, D16, D20, D24, D30, D60）
# ------------------------------------------------------------
st.header("2. 出力方法の設定")
with st.expander("クリックで展開", expanded=False):

    col_op1, col_op2 = st.columns(2)

    with col_op1:
        node_ui = st.radio(
            "ノードの計算",
            ["Mean Node (平均)", "True Node (真位置)"],
            horizontal=True
        )
        is_true_node = node_ui.startswith("True")

        use_compact_planet = st.checkbox(
            "惑星キー・サイン名を短縮（Sun→Su, Aries→Ari）", value=True
        )
        use_short_sd = st.checkbox(
            "Sign/Degree キーも短縮（sg/deg）", value=False
        )
        minify_json = st.checkbox("JSONを最小化（スペース・改行なし）", value=True)

        # D1 専用：ナクシャトラ出力トグル
        use_nak_single = st.checkbox(
            "D1のナクシャトラを短縮 'nak'（例: Sata-3 / UBha-3）で出力", value=True
        )

    with col_op2:
        st.write("出力する分割図（複数選択）")
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

    swe.set_sid_mode(swe.SIDM_LAHIRI)

    def _map_gender_to_en(g):
        if g == "男性": return "male"
        if g == "女性": return "female"
        return "unknown"

    gender_ai = _map_gender_to_en(gender)

    # ローカル時刻 → UT
    hour_local = h + m/60 + s/3600
    hour_utc   = hour_local - tz
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_utc)

    charts = {}

    # --- D1: 速度（丸めなし）＆ナクシャトラ（Asc 先頭） ---
    if d1:
        charts["D1_Rashi"] = get_varga_data(
            jd, 1, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=True,
            include_nakshatra=True,
            nak_single=use_nak_single,
            asc_first=True
        )

    # --- その他の分割図（Asc 先頭、速度/ナクシャトラなし） ---
    if d9:
        charts["D9_Navamsa"] = get_varga_data(
            jd, 9, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d3:
        charts["D3_Drekkana"] = get_varga_data(
            jd, 3, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d4:
        charts["D4_Chaturthamsa"] = get_varga_data(
            jd, 4, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d7:
        charts["D7_Saptamsa"] = get_varga_data(
            jd, 7, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d10:
        charts["D10_Dasamsa"] = get_varga_data(
            jd, 10, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d12:
        charts["D12_Dwadasamsa"] = get_varga_data(
            jd, 12, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d16:
        charts["D16_Shodasamsa"] = get_varga_data(
            jd, 16, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d20:
        charts["D20_Vimsamsa"] = get_varga_data(
            jd, 20, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d24:
        charts["D24_Chaturvimsamsa"] = get_varga_data(
            jd, 24, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d30:
        charts["D30_Trimsamsa"] = get_varga_data(
            jd, 30, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )
    if d60:
        charts["D60_Shashtyamsa"] = get_varga_data(
            jd, 60, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False,
            include_nakshatra=False,
            asc_first=True
        )

    node_value_for_json = "True" if is_true_node else "Mean"

    final_output = {
        "User_Profile": {
            "Name": user_name,
            "Gender": gender_ai,
            "Birth": f"{birth_date} {h:02d}:{m:02d}:{s:02d}",
            "Location": {"Lat": round(float(lat), 6), "Lon": round(float(lon), 6)},
            "Settings": {
                "Node": node_value_for_json,   # 英語のみ
                "Ayanamsa": "Lahiri",
                "UTC_Offset": tz
            },
        },
        "Instructions": custom_prompt,
        "Charts": charts
    }

    # JSON 出力
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
