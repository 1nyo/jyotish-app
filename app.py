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

# 短縮表記（例: "Sata" / "UBha"）
NAK_ABBR = {
    "Ashwini":"Ashw","Bharani":"Bhar","Krittika":"Krit","Rohini":"Rohi","Mrigashira":"Mri",
    "Ardra":"Ardr","Punarvasu":"Puna","Pushya":"Push","Ashlesha":"Ashl","Magha":"Magh",
    "Purva Phalguni":"PPhal","Uttara Phalguni":"UPhal","Hasta":"Hast","Chitra":"Chit","Swati":"Swat",
    "Vishakha":"Vish","Anuradha":"Anur","Jyeshtha":"Jyes","Mula":"Mula","Purva Ashadha":"PAsh",
    "Uttara Ashadha":"UAsh","Shravana":"Shra","Dhanishta":"Dhan","Shatabhisha":"Sata",
    "Purva Bhadrapada":"PBha","Uttara Bhadrapada":"UBha","Revati":"Reva"
}

def map_gender_to_en(g):
    if g == "男性": return "male"
    if g == "女性": return "female"
    return "unknown"

# ---- ナクシャトラ算出（名称・Pada） ----
def compute_nakshatra(lon_deg: float):
    """
    lon_deg: 恒星帯の黄経（度, 0-360）
    戻り値: (nak_name, pada[1..4])
    """
    lon = lon_deg % 360.0
    unit = 360.0 / 27.0  # 13.333...°
    idx = int(lon // unit)                   # 0..26
    pada = int(((lon % unit) // (unit/4.0))) + 1  # 1..4
    return NAK_NAMES[idx], pada

def format_nak_abbr(nak_name: str, pada: int) -> str:
    """短縮 'nak' 形式（例：'Sata-3' / 'UBha-3'）"""
    abbr = NAK_ABBR.get(nak_name, nak_name[:4])
    return f"{abbr}-{pada}"

# ------------------------------------------------------------
# Varga 計算
#   - 角度は小数点2桁
#   - Asc は tropical→sidereal へ変換（ayanamsha を減算）してから出力
#   - 各チャートで Asc を先頭に出力（asc_first=True）
#   - D1 のみ：速度（Speed, deg/day, 小数点3桁）とナクシャトラ（形式トグル）を付与
#   - 惑星速度取得のため calc_ut flags に FLG_SPEED を付与
# ------------------------------------------------------------
# ====== ここから計算ユーティリティ（補助関数） ======

def _sign_index(lon_sid):  # 0..11
    return int((lon_sid % 360.0) // 30.0)

def _deg_in_sign(lon_sid):  # 0..30
    return (lon_sid % 30.0)

def _scale_deg_to_30(within_deg, seg_size):
    """区画内の [0..seg_size) を [0..30) に線形拡大（不等分割D30向け）"""
    return (within_deg / seg_size) * 30.0

# --- D3 Drekkana（等分）: 10°×3、割当は 1st=同サイン, 2nd=5th, 3rd=9th ---
def varga_pos_d3(lon_sid):
    base = _sign_index(lon_sid)
    deg  = _deg_in_sign(lon_sid)
    k = int(deg // 10.0)  # 0,1,2
    to_add = [0, 4, 8][k]  # +0,+4,+8
    sign = (base + to_add) % 12
    deg30 = ((lon_sid * 3.0) % 30.0)  # 等分は倍角でOK
    return sign, deg30

# --- D9 Navamsa（等分）: 3°20′×9、起点= 可動:同/ 不動:9th/ 双体:5th ---
def varga_pos_d9(lon_sid):
    base = _sign_index(lon_sid)
    deg  = _deg_in_sign(lon_sid)
    seg  = 30.0/9.0  # 3.333...
    k = int(deg // seg)  # 0..8
    modality = base % 3  # 可動0, 固定1, 双体2 （Ar=0, Ta=1, Ge=2, ...）
    start_add = {0:0, 1:8, 2:4}[modality]  # 同/9th/5th
    sign = (base + start_add + k) % 12
    deg30 = ((lon_sid * 9.0) % 30.0)
    return sign, deg30

# --- D10 Dashamsa（等分）: 3°×10、起点= 奇数:同/ 偶数:9th ---
def varga_pos_d10(lon_sid):
    base = _sign_index(lon_sid)
    deg  = _deg_in_sign(lon_sid)
    seg  = 3.0
    k = int(deg // seg)  # 0..9
    start_add = 0 if (base % 2 == 0) else 8  # base=0:Aries(奇数サイン)→同, 1:Taurus(偶数)→9th
    # 注意: ここでは 0=Aries を奇数扱いにしています（0,2,4..が奇数サイン）
    # 12サインの配列上、index偶数=奇数サインという実装表現です
    sign = (base + start_add + k) % 12
    deg30 = ((lon_sid * 10.0) % 30.0)
    return sign, deg30

# --- D12 Dwadasamsa（等分）: 2.5°×12、起点=同サイン ---
def varga_pos_d12(lon_sid):
    base = _sign_index(lon_sid)
    deg30 = ((lon_sid * 12.0) % 30.0)
    # 2.5°ごとにサインが1つ進む → 倍角でOK（起点=同）
    add = int((_deg_in_sign(lon_sid)) // (30.0/12.0))
    sign = (base + add) % 12
    return sign, deg30

# --- D16 Shodasamsa（等分）: 1°52'30"×16、起点規則（一般的実装）=奇数:同/ 偶数:9th ---
def varga_pos_d16(lon_sid):
    base = _sign_index(lon_sid)
    seg  = 30.0/16.0
    k = int(_deg_in_sign(lon_sid) // seg)
    start_add = 0 if (base % 2 == 0) else 8
    sign = (base + start_add + k) % 12
    deg30 = ((lon_sid * 16.0) % 30.0)
    return sign, deg30

# --- D20 Vimsamsa（等分）: 1°30′×20、起点= 可動:Ar/ 固定:Sag/ 双体:Leo ---
def varga_pos_d20(lon_sid):
    base = _sign_index(lon_sid)
    seg  = 30.0/20.0
    k = int(_deg_in_sign(lon_sid) // seg)  # 0..19
    modality = base % 3  # 可動0/固定1/双体2
    starts = {0:0, 1:8, 2:4}  # Aries/Sag/Leo 起点 → baseからのオフセット
    sign = (starts[modality] + k) % 12
    deg30 = ((lon_sid * 20.0) % 30.0)
    return sign, deg30

# --- D24 Chaturvimsamsa（等分）: 1°15′×24、（簡易）奇数:同/ 偶数:9th 起点
def varga_pos_d24(lon_sid):
    base = _sign_index(lon_sid)
    seg  = 30.0/24.0
    k = int(_deg_in_sign(lon_sid) // seg)
    start_add = 0 if (base % 2 == 0) else 8
    sign = (base + start_add + k) % 12
    deg30 = ((lon_sid * 24.0) % 30.0)
    return sign, deg30

# --- D30 Trimsamsa（不等分）: 奇数サイン=5/5/8/7/5°, 偶数サイン=5/5/8/7/5°（順序逆）
def varga_pos_d30(lon_sid):
    base = _sign_index(lon_sid)
    deg  = _deg_in_sign(lon_sid)
    # 区画サイズ（度）と割当サインの進み方（奇偶で反転）
    odd_sizes  = [5.0, 5.0, 8.0, 7.0, 5.0]   # 奇数サイン
    even_sizes = [5.0, 7.0, 8.0, 5.0, 5.0]   # 偶数サイン（多くの流派で奇数の逆順を採用）
    sizes = odd_sizes if (base % 2 == 0) else even_sizes
    # どの区画に入るかを決める
    acc = 0.0
    idx = 0
    for i, w in enumerate(sizes):
        if deg < acc + w:
            idx = i
            break
        acc += w
    # 区画 idx ぶんサインを進める
    sign = (base + idx) % 12
    # 区画内の位置を 0..30° にスケール
    within = deg - sum(sizes[:idx])
    deg30 = _scale_deg_to_30(within, sizes[idx])
    return sign, deg30

# --- D60 Shashtiamsa（等分）: 0.5°×60、（簡易）起点=同サイン
def varga_pos_d60(lon_sid):
    base = _sign_index(lon_sid)
    seg  = 30.0/60.0  # 0.5°
    k = int(_deg_in_sign(lon_sid) // seg)  # 0..59
    sign = (base + k) % 12
    deg30 = ((lon_sid * 60.0) % 30.0)
    return sign, deg30

def varga_pos_dispatch(varga_n, lon_sid):
    """varga_n に応じて上の関数へ振り分ける"""
    if varga_n == 1:   # D1
        return _sign_index(lon_sid), _deg_in_sign(lon_sid)
    if varga_n == 3:   return varga_pos_d3(lon_sid)
    if varga_n == 4:   # D4（簡易：等分×起点=奇数:同/偶数:9th）
        base = _sign_index(lon_sid); seg=30/4; k=int(_deg_in_sign(lon_sid)//seg)
        start_add = 0 if (base%2==0) else 8
        return (base+start_add+k)%12, ((lon_sid*4)%30)
    if varga_n == 7:   # D7（簡易：等分×起点=奇数:同/偶数:7th）
        base=_sign_index(lon_sid); seg=30/7; k=int(_deg_in_sign(lon_sid)//seg)
        start_add = 0 if (base%2==0) else 6
        return (base+start_add+k)%12, ((lon_sid*7)%30)
    if varga_n == 9:   return varga_pos_d9(lon_sid)
    if varga_n == 10:  return varga_pos_d10(lon_sid)
    if varga_n == 12:  return varga_pos_d12(lon_sid)
    if varga_n == 16:  return varga_pos_d16(lon_sid)
    if varga_n == 20:  return varga_pos_d20(lon_sid)
    if varga_n == 24:  return varga_pos_d24(lon_sid)
    if varga_n == 30:  return varga_pos_d30(lon_sid)
    if varga_n == 60:  return varga_pos_d60(lon_sid)
    # フォールバック：従来の倍角法（合わないVargaがあるので早期に全置換推奨）
    vlon = (lon_sid * varga_n) % 360.0
    return int(vlon // 30.0), (vlon % 30.0)

# ====== ここから本体の Varga 計算 ======

def get_varga_data(
    jd, varga_factor, is_true_node, lat, lon,
    compact_planet=False, short_sd_keys=False,
    include_speed=False, include_nakshatra=False,
    nak_single=False, asc_first=True
):
    key_sign = "sg" if short_sd_keys else "Sign"
    key_deg  = "deg" if short_sd_keys else "Degree"
    signs_full = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio",
                  "Sagittarius","Capricorn","Aquarius","Pisces"]
    sig = SIG_ABBR if compact_planet else signs_full
    out = {}

    # --- Asc（恒星帯）：tropical ASC - ayanamsha で sidereal ASC → Varga 位置へ ---
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P')    # tropical Asc
    asc_trop = (ascmc[0] % 360.0)
    ayan = swe.get_ayanamsa_ut(jd)
    asc_sid = (asc_trop - ayan) % 360.0
    asc_s, asc_d = varga_pos_dispatch(varga_factor, asc_sid)
    asc_key = PLANET_ABBR.get("Ascendant","Ascendant") if compact_planet else "Ascendant"
    asc_obj = {key_sign: sig[asc_s], key_deg: round(asc_d, 2)}
    # D1のみ：ナクシャトラを付与する指定がある場合
    if include_nakshatra and varga_factor == 1:
        nk_name_a, nk_pada_a = compute_nakshatra(asc_sid)
        if nak_single:
            asc_obj["nak"] = format_nak_abbr(nk_name_a, nk_pada_a)
        else:
            asc_obj["Nakshatra"] = nk_name_a
            asc_obj["Pada"] = nk_pada_a
    if asc_first:
        out[asc_key] = asc_obj

    # --- 惑星群（速度取得は FLG_SPEED を必ず指定） ---
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN
    }
    planets["Rahu"] = swe.TRUE_NODE if is_true_node else swe.MEAN_NODE
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    for name, pid in planets.items():
        res, _ = swe.calc_ut(jd, pid, flags)
        lon_sid = res[0] % 360.0
        spd     = res[3]  # deg/day

        vs, vd = varga_pos_dispatch(varga_factor, lon_sid)
        key_out = PLANET_ABBR.get(name, name) if compact_planet else name
        base = {key_sign: sig[vs], key_deg: round(vd, 2)}

        # D1 のみ速度・ナクシャトラ対応
        if varga_factor == 1:
            # Speed（小数点3桁）
            if include_speed:
                base["Speed"] = round(spd, 3)
            if include_nakshatra:
                nk_name, nk_pada = compute_nakshatra(lon_sid)
                if nak_single:
                    base["nak"] = format_nak_abbr(nk_name, nk_pada)
                else:
                    base["Nakshatra"] = nk_name
                    base["Pada"] = nk_pada

        out[key_out] = base

        # Ketu（Rahu と対向）
        if name == "Rahu":
            k_lon_sid = (lon_sid + 180.0) % 360.0
            ks, kd = varga_pos_dispatch(varga_factor, k_lon_sid)
            kkey = PLANET_ABBR.get("Ketu","Ketu") if compact_planet else "Ketu"
            base_k = {key_sign: sig[ks], key_deg: round(kd, 2)}
            if varga_factor == 1 and include_speed:
                base_k["Speed"] = None
            if varga_factor == 1 and include_nakshatra:
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

        # D1 専用：ナクシャトラ 'nak' 形式トグル
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

    # 恒星帯：Lahiri
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    gender_ai = map_gender_to_en(gender)

    # ローカル時刻 → UT
    hour_local = h + m/60 + s/3600
    hour_utc   = hour_local - tz
    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour_utc)

    charts = {}

    # --- D1: 速度(3桁)＆ナクシャトラ（Asc 先頭） ---
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
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d3:
        charts["D3_Drekkana"] = get_varga_data(
            jd, 3, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d4:
        charts["D4_Chaturthamsa"] = get_varga_data(
            jd, 4, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d7:
        charts["D7_Saptamsa"] = get_varga_data(
            jd, 7, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d10:
        charts["D10_Dasamsa"] = get_varga_data(
            jd, 10, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d12:
        charts["D12_Dwadasamsa"] = get_varga_data(
            jd, 12, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d16:
        charts["D16_Shodasamsa"] = get_varga_data(
            jd, 16, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d20:
        charts["D20_Vimsamsa"] = get_varga_data(
            jd, 20, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d24:
        charts["D24_Chaturvimsamsa"] = get_varga_data(
            jd, 24, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d30:
        charts["D30_Trimsamsa"] = get_varga_data(
            jd, 30, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
        )
    if d60:
        charts["D60_Shashtyamsa"] = get_varga_data(
            jd, 60, is_true_node, lat, lon,
            compact_planet=use_compact_planet,
            short_sd_keys=use_short_sd,
            include_speed=False, include_nakshatra=False, asc_first=True
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
