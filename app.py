# app.py — AI専用ヴェーダ占星術データ抽出（JH互換 Varga エンジン統合版）
# - 都市検索なし / 緯度・経度・UTCは手入力（1行）
# - 出生日・出生時刻（時/分/秒）は1行
# - D1のみ：Speed(度/日・小数点3桁) と ナクシャトラ（nak 形式トグル）を付与
# - Sign/Degree → sg/deg のキー短縮トグル、惑星キー・サイン略号のトグル
# - Varga計算は third_party/jyotishyamitra/mod_divisional.py を最優先（JH互換）
# - フォールバック計算も内蔵（非常用）

import streamlit as st
import swisseph as swe
import json
from datetime import date

# ------------------------------------------------------------
# ページ設定
# ------------------------------------------------------------
st.set_page_config(page_title="AI Jyotish Data Generator", layout="wide")
st.title("🌌 AI専用ヴェーダ占星術データ抽出（JH互換 Varga）")

# ------------------------------------------------------------
# 外部 Varga エンジン（jyotishyamitra）読み込み（パッケージ→直読みの順で試行）
# ------------------------------------------------------------
import importlib.util
from pathlib import Path
import sys

HAS_JM = False
dv = None

# ① パッケージ読み込みを試す
try:
    from third_party.jyotishyamitra import mod_divisional as dv
    HAS_JM = True
except Exception:
    HAS_JM = False

# ② 失敗時：app.py の場所から絶対パス指定で直読み
if not HAS_JM:
    try:
        base_dir = Path(__file__).resolve().parent  # app.py があるディレクトリ
        mod_path = base_dir / "third_party" / "jyotishyamitra" / "mod_divisional.py"
        if mod_path.exists():
            spec = importlib.util.spec_from_file_location("jm_mod_divisional", str(mod_path))
            dv = importlib.util.module_from_spec(spec)  # type: ignore
            assert spec and spec.loader
            spec.loader.exec_module(dv)  # type: ignore
            HAS_JM = True
    except Exception:
        HAS_JM = False

# デバッグ表示（成否とどこから読んだかが分かる）
if HAS_JM and dv is not None:
    st.caption(f"[JM] loaded: {getattr(dv, '__file__', 'unknown')}")
else:
    st.caption("[JM] NOT loaded (fallback mode)")

# ------------------------------------------------------------
# 惑星キー短縮・サイン略号
# ------------------------------------------------------------
PLANET_ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
    "Rahu": "Ra", "Ketu": "Ke", "Ascendant": "Asc"
}

SIG_FULL = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
            "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIG_ABBR = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]

_SIG_INDEX = {name.lower(): i for i, name in enumerate(SIG_FULL)}
_SIG_INDEX.update({abbr.lower(): i for i, abbr in enumerate(SIG_ABBR)})

def normalize_sign_to_index(sign):
    """sign が 0..11 / 1..12 / 'Aries' / 'Ari' 等どれで来ても 0..11 に正規化"""
    if isinstance(sign, int):
        if 0 <= sign <= 11:
            return sign
        if 1 <= sign <= 12:
            return sign - 1
    if isinstance(sign, str):
        key = sign.strip().lower()
        return _SIG_INDEX.get(key, None)
    return None

def deg_to_2dec(x):  # 角度は 2 桁
    return round(float(x), 2)

def spd_to_3dec(x):  # Speed は 3 桁
    return round(float(x), 3)

def map_gender_to_en(g):
    if g == "男性": return "male"
    if g == "女性": return "female"
    return "unknown"

# ------------------------------------------------------------
# ナクシャトラ（D1のみ）
# ------------------------------------------------------------
NAK_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha",
    "Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada",
    "Uttara Bhadrapada","Revati"
]

# 短縮表記（例：「Sata-3」/「UBha-2」）
NAK_ABBR = {
    "Ashwini":"Ashw","Bharani":"Bhar","Krittika":"Krit","Rohini":"Rohi","Mrigashira":"Mri",
    "Ardra":"Ardr","Punarvasu":"Puna","Pushya":"Push","Ashlesha":"Ashl","Magha":"Magh",
    "Purva Phalguni":"PPhal","Uttara Phalguni":"UPhal","Hasta":"Hast","Chitra":"Chit","Swati":"Swat",
    "Vishakha":"Vish","Anuradha":"Anur","Jyeshtha":"Jyes","Mula":"Mula","Purva Ashadha":"PAsh",
    "Uttara Ashadha":"UAsh","Shravana":"Shra","Dhanishta":"Dhan","Shatabhisha":"Sata",
    "Purva Bhadrapada":"PBha","Uttara Bhadrapada":"UBha","Revati":"Reva"
}

def compute_nakshatra(lon_deg: float):
    """
    lon_deg: 恒星帯の黄経（度, 0-360）
    戻り値: (nak_name, pada[1..4])
    """
    lon = lon_deg % 360.0
    unit = 360.0 / 27.0  # 13.333...°
    idx = int(lon // unit)  # 0..26
    pada = int(((lon % unit) // (unit / 4.0))) + 1  # 1..4
    return NAK_NAMES[idx], pada

def format_nak_abbr(nak_name: str, pada: int) -> str:
    abbr = NAK_ABBR.get(nak_name, nak_name[:4])
    return f"{abbr}-{pada}"

# ------------------------------------------------------------
# jyotishyamitra（mod_divisional）のアダプタ
# ------------------------------------------------------------
def _jm_map_varga(lon_sid: float, varga_n: int):
    """
    sidereal 黄経 lon_sid → (sign_index 0..11, degree_in_sign 0..30) を返す。
    - third_party/jyotishyamitra/mod_divisional.py の get_divisional_sign_and_degree を使用
    - 失敗時は None（＝フォールバック使用）
    """
    if not HAS_JM or dv is None:
        return None
    try:
        if hasattr(dv, "get_divisional_sign_and_degree"):
            out = dv.get_divisional_sign_and_degree(lon_sid, varga_n)
            # 期待形式: (sign, deg) — sign は 0..11 / 1..12 / 'Aries' / 'Ari' のいずれか
            if isinstance(out, (tuple, list)) and len(out) >= 2:
                s_idx = normalize_sign_to_index(out[0])
                if s_idx is None and isinstance(out[0], (int, float)):
                    s_idx = normalize_sign_to_index(int(out[0]))
                if s_idx is None:
                    return None
                return s_idx, float(out[1])
    except Exception:
        return None
    return None

# ------------------------------------------------------------
# フォールバック（JMが使えない場合の保険）
# ------------------------------------------------------------
def _fallback_varga_mapping(lon_sid: float, varga_n: int):
    """
    JM が使えない場合の簡易マッピング。
    D9/D10/D20 の起点規則、D30 の不等分（5/5/8/7/5）だけは押さえ、
    他は等分×同サイン起点の素直な割当（安全側の簡易）。
    戻り値: (sign_index 0..11, degree_in_sign[0..30))
    """
    base = int((lon_sid % 360.0) // 30.0)
    xdeg = (lon_sid % 30.0)

    def d_equal(seg, start_add=0):
        k = int(xdeg // seg)
        s = (base + start_add + k) % 12
        deg30 = (lon_sid * (30.0/seg)) % 30.0
        return s, deg30

    # D9: 可動=同, 固定=9th, 双体=5th
    if varga_n == 9:
        modality = base % 3
        start_add = {0:0,1:8,2:4}[modality]
        return d_equal(30.0/9.0, start_add)

    # D10: 奇数=同 / 偶数=9th（index 偶数を奇数サインとみなす実装）
    if varga_n == 10:
        start_add = 0 if (base % 2 == 0) else 8
        return d_equal(3.0, start_add)

    # D20: 可動=Ar, 固定=Sag, 双体=Leo 起点
    if varga_n == 20:
        k = int(xdeg // (30.0/20.0))
        starts = {0:0,1:8,2:4}
        modality = base % 3
        s = (starts[modality] + k) % 12
        deg30 = (lon_sid * 20.0) % 30.0
        return s, deg30

    # D30: 不等分（奇数=5,5,8,7,5 / 偶数=5,7,8,5,5）
    if varga_n == 30:
        odd_sizes  = [5.0, 5.0, 8.0, 7.0, 5.0]
        even_sizes = [5.0, 7.0, 8.0, 5.0, 5.0]
        sizes = odd_sizes if (base % 2 == 0) else even_sizes
        acc = 0.0
        idx = 0
        for i, w in enumerate(sizes):
            if xdeg < acc + w:
                idx = i
                break
            acc += w
        s = (base + idx) % 12
        within = xdeg - sum(sizes[:idx])
        deg30 = (within / sizes[idx]) * 30.0
        return s, deg30

    # D12/D16/D24/D60/D3/D4/D7 などは等分×同サイン起点
    if varga_n in (12, 16, 24, 60, 3, 4, 7):
        seg = 30.0 / float(varga_n)
        return d_equal(seg, 0)

    # 最後の手段：単純倍角
    vlon = (lon_sid * varga_n) % 360.0
    return int(vlon // 30.0), (vlon % 30.0)

# ------------------------------------------------------------
# Varga 計算本体
# ------------------------------------------------------------
def get_varga_data(
    jd, varga_factor, is_true_node, lat, lon,
    compact_planet=False, short_sd_keys=False,
    include_speed=False, include_nakshatra=False,
    nak_single=False, asc_first=True
):
    key_sign = "sg" if short_sd_keys else "Sign"
    key_deg  = "deg" if short_sd_keys else "Degree"
    sig_out  = SIG_ABBR if compact_planet else SIG_FULL

    out = {}

    # ---- Asc tropical→sidereal→Varga ----
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P')    # tropical Asc
    asc_trop = (ascmc[0] % 360.0)
    ayan = swe.get_ayanamsa_ut(jd)
    asc_sid = (asc_trop - ayan) % 360.0

    asc_map = _jm_map_varga(asc_sid, varga_factor)
    if asc_map is None:
        s_idx, deg30 = _fallback_varga_mapping(asc_sid, varga_factor)
    else:
        s_idx, deg30 = asc_map[0], asc_map[1] % 30.0

    asc_obj = {key_sign: sig_out[s_idx], key_deg: deg_to_2dec(deg30)}
    akey  = PLANET_ABBR.get("Ascendant","Ascendant") if compact_planet else "Ascendant"

    if include_nakshatra and varga_factor == 1:
        nk_name_a, nk_pada_a = compute_nakshatra(asc_sid)
        if nak_single:
            asc_obj["nak"] = format_nak_abbr(nk_name_a, nk_pada_a)
        else:
            asc_obj["Nakshatra"] = nk_name_a
            asc_obj["Pada"] = nk_pada_a

    if asc_first:
        out[akey] = asc_obj

    # ---- 惑星群（恒星帯+速度）----
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
        spd     = res[3]

        mp = _jm_map_varga(lon_sid, varga_factor)
        if mp is None:
            s_idx, deg30 = _fallback_varga_mapping(lon_sid, varga_factor)
        else:
            s_idx, deg30 = mp[0], mp[1] % 30.0

        key_out = PLANET_ABBR.get(name, name) if compact_planet else name
        base = {key_sign: sig_out[s_idx], key_deg: deg_to_2dec(deg30)}

        if varga_factor == 1:
            if include_speed:
                base["Speed"] = spd_to_3dec(spd)   # 3桁
            if include_nakshatra:
                nk_name, nk_pada = compute_nakshatra(lon_sid)
                if nak_single:
                    base["nak"] = format_nak_abbr(nk_name, nk_pada)
                else:
                    base["Nakshatra"] = nk_name
                    base["Pada"] = nk_pada

        out[key_out] = base

        # --- Ketu（Rahu と対向）---
        if name == "Rahu":
            k_lon_sid = (lon_sid + 180.0) % 360.0
            mpk = _jm_map_varga(k_lon_sid, varga_factor)
            if mpk is None:
                ks_idx, kdeg30 = _fallback_varga_mapping(k_lon_sid, varga_factor)
            else:
                ks_idx, kdeg30 = mpk[0], mpk[1] % 30.0

            kkey = PLANET_ABBR.get("Ketu","Ketu") if compact_planet else "Ketu"
            base_k = {key_sign: sig_out[ks_idx], key_deg: deg_to_2dec(kdeg30)}
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

    st.success(f"生成完了（外部Vargaエンジン読み込み: {HAS_JM}）")
