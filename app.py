# app.py
# -*- coding: utf-8 -*-
"""
AI用 Jyotish データ作成ツール（キャッシュ最適化版）
- Streamlit + Swiss Ephemeris + 分割図（D1/D9/D20/D60）
- 計算負荷を @st.cache_data / @st.cache_resource で軽減
"""

import json
from datetime import date
import streamlit as st
import swisseph as swe

# ---- calc modules ----
from calc.ephemeris import (
    setup_sidereal,
    jd_ut_from_local,
    ayanamsa_deg,
    asc_sidereal,
    planet_sidereal_longitudes,
)
from calc.d1 import build_d1
from calc.d9 import build_d9
from calc.d20 import build_d20
from calc.d60 import build_d60
from calc.validators import prune_and_validate


# ----------------------
# Helpers
# ----------------------
def format_tz(offset: float) -> str:
    """UTC ±h を文字列化（例：UTC+9 / UTC-5.5）"""
    sign = "+" if offset >= 0 else "-"
    val = abs(offset)
    if abs(val - int(val)) < 1e-9:
        return f"UTC{sign}{int(val)}"
    return f"UTC{sign}{val:.1f}"


def deg_to_dms_str(deg: float, always_sign_minus=False) -> str:
    """
    23.565 -> "-23:33:54" 風に整形。
    always_sign_minus=True の時は “-" で出す（アヤナーンシャ表記向け）。
    """
    d = abs(deg)
    D = int(d)
    m_f = (d - D) * 60
    M = int(m_f)
    S = int(round((m_f - M) * 60))
    if S == 60:
        S = 0
        M += 1
    if M == 60:
        M = 0
        D += 1
    prefix = "-" if always_sign_minus else ""
    return f"{prefix}{D:02d}:{M:02d}:{S:02d}"


# =======================================================
# Streamlit page
# =======================================================
st.set_page_config(page_title="AI用 Jyotish データ作成ツール", layout="wide")
st.title("AI用 Jyotish データ作成ツール（キャッシュ最適化版）")


# =======================================================
# 0) キャッシュ：Ephemeris 初期化（パス・サイデリアル）
# =======================================================
@st.cache_resource(show_spinner=False)
def init_ephemeris(ephe_path: str, ayan_mode: str = "Lahiri_ICRC") -> bool:
    """
    Swiss Ephemeris の初期設定。
    - ephe_path: パス（空なら None）
    - ayan_mode: 'Lahiri_ICRC' or 'Lahiri'（calc/ephemeris.setup_sidereal 内でフォールバック）
    返り値はダミー（True）。初期化は一度だけ。
    """
    try:
        swe.set_ephe_path(ephe_path if ephe_path.strip() else None)
    except Exception:
        swe.set_ephe_path(None)
    setup_sidereal(ayan_mode)
    return True


# =======================================================
# 1) 入力UI
# =======================================================
st.header("1. 出生情報の入力")
with st.container(border=True):
    c1, c2 = st.columns([1.5, 1])
    with c1:
        user_name = st.text_input("名前", value="Guest")
        location_label = st.text_input("出生地（任意ラベル）", value="Unknown")
    with c2:
        gender = st.selectbox("性別", ["不明", "男性", "女性", "その他"], index=0)

    st.write("出生日・時刻（24時間制）")
    d1c, d2c, d3c, d4c = st.columns([1.8, 1, 1, 1])
    with d1c:
        birth_date = st.date_input("出生日", value=date(1990, 1, 1))
    with d2c:
        h = st.selectbox("時", list(range(0, 24)), index=12)
    with d3c:
        m = st.selectbox("分", list(range(0, 60)), index=0)
    with d4c:
        s = st.selectbox("秒", list(range(0, 60)), index=0)

    st.write("出生地（緯度・経度・UTCオフセット）初期値は東京")
    g1, g2, g3 = st.columns([1, 1, 1])
    with g1:
        lat = st.number_input("緯度（北緯+／南緯-）", value=35.68000, format="%.6f")
    with g2:
        lon = st.number_input("経度（東経+／西経-）", value=139.75000, format="%.6f")
    with g3:
        tz_offset = st.number_input("UTCオフセット", value=9.0, step=0.5, format="%.1f")


# =======================================================
# 2) 出力設定UI
# =======================================================
st.header("2. 出力方法の設定")
with st.expander("クリックで展開", expanded=True):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        node_type_label = st.radio("ノードの計算", ["True Node（真）", "Mean Node（平均）"], index=0)
        ck_mode_label = st.radio("Chara Karaka", ["7（Rahu除外）", "8（Rahu含む）"], index=0)
        include_lordship = st.checkbox("支配関係を出力に含む", value=True)
    with col2:
        include_d1 = st.checkbox("D1 Rashi（基本）", value=True)
        include_d9 = st.checkbox("D9 Navamsa（本質層）", value=True)
        include_d20 = st.checkbox("D20 Vimsamsa（精神性、宗教）", value=False)
        include_d60 = st.checkbox("D60 Shashtyamsa（深層カルマ）", value=False)
    with col3:
        minimize = st.checkbox("出力するJSONを最小化（スペース・改行なし）", value=True)
        ephe_path = st.text_input("Swiss Ephemeris ファイルパス（空で内蔵）", value="")
        # キャッシュ・ポリシー（必要に応じて調整）
        ttl_sec = st.number_input("キャッシュTTL（秒）※0は無制限", value=0, min_value=0)


# =======================================================
# 3) キャッシュ：コア計算（Asc/惑星/アヤナーンシャ）
#    入力パラメータが同じなら再計算しない
# =======================================================
@st.cache_data(show_spinner=True)
def compute_core(
    y: int,
    mo: int,
    d: int,
    h_float: float,
    tz: float,
    lat_deg: float,
    lon_deg: float,
    node_flag: str,  # "True" | "Mean"
    ephe_inited_key: bool,  # init_ephemeris の結果（True）
) -> dict:
    """
    重いコア計算部分（Asc/惑星/アヤナーンシャ）
    ※ ephe_inited_key はキャッシュキー用ダミー（True）：
       先に init_ephemeris(...) が評価済み（= パス/サイデリアル設定済み）であることを保証
    """
    jd_ut = jd_ut_from_local(y, mo, d, h_float, tz)
    asc = asc_sidereal(jd_ut, lat_deg, lon_deg)
    planets = planet_sidereal_longitudes(jd_ut, node_flag)
    aya = ayanamsa_deg(jd_ut)
    return {"jd_ut": jd_ut, "asc": asc, "planets": planets, "ayanamsa": aya}


# =======================================================
# 4) キャッシュ：Varga生成（D1/D9/D20/D60）
# =======================================================
@st.cache_data(show_spinner=False)
def build_vargas(
    asc: float,
    planets: dict,
    ck_mode: str,               # "7" | "8"
    include_lordship: bool,
    need_d1: bool,
    need_d9: bool,
    need_d20: bool,
    need_d60: bool,
) -> dict:
    """
    各分割図の JSON 断片を生成（必要なものだけ）
    """
    out = {}
    opts = {"ck_mode": ck_mode, "include_lordship": include_lordship}

    if need_d1:
        out["D1"] = build_d1(asc, planets, opts)
    if need_d9:
        out["D9"] = build_d9(asc, planets)
    if need_d20:
        out["D20"] = build_d20(asc, planets)
    if need_d60:
        out["D60"] = build_d60(asc, planets)
    return out


# =======================================================
# 5) ボタン押下 → 生成
# =======================================================
go = st.button("AI向けJSONを生成", type="primary")

if go:
    # 5-1) Ephemeris 初期化（キャッシュ済み）
    inited = init_ephemeris(ephe_path, "Lahiri_ICRC")

    # 5-2) パラメータ整備
    h_float = int(h) + int(m) / 60.0 + int(s) / 3600.0
    node_flag = "True" if node_type_label.startswith("True") else "Mean"
    ck_mode = "8" if ck_mode_label.startswith("8") else "7"

    # 5-3) コア計算（Asc/惑星/アヤナーンシャ）— キャッシュ
    core = compute_core(
        birth_date.year,
        birth_date.month,
        birth_date.day,
        h_float,
        tz_offset,
        lat,
        lon,
        node_flag,
        inited,  # True
    )

    asc = core["asc"]
    planets = core["planets"]
    aya_val = core["ayanamsa"]
    aya_str = deg_to_dms_str(aya_val, always_sign_minus=True)

    # 5-4) Varga 生成 — キャッシュ
    vargas = build_vargas(
        asc,
        planets,
        ck_mode,
        include_lordship,
        include_d1,
        include_d9,
        include_d20,
        include_d60,
    )

    # 5-5) D9 がある場合、karakamsa_sign を D1 へ注入
    if include_d1 and include_d9 and ("D1" in vargas) and ("D9" in vargas):
        try:
            ak_planet = vargas["D1"].get("jaimini", {}).get("AK")
            if ak_planet:
                karaka_sign = vargas["D9"]["planets"][ak_planet]["sign"]
                vargas["D1"].setdefault("jaimini", {})["karakamsa_sign"] = karaka_sign
        except Exception:
            pass

    # 5-6) meta 構築
    meta = {
        "name": user_name,
        "birth": f"{birth_date.isoformat()} {int(h):02d}:{int(m):02d}",
        "timezone": format_tz(tz_offset),
        "latitude": f"{lat:.2f}",
        "longitude": f"{lon:.2f}",
        "location": location_label,
        "ayanamsa": f"Lahiri ICRC {aya_str}",
        "calculation_model": "Drik Siddhanta",
        "node_type": node_flag,
        "house_system": "Whole Sign",
    }

    # 5-7) トップレベル JSON まとめ → バリデーション → 表示
    out = {"meta": meta}
    out.update(vargas)
    out = prune_and_validate(out)

    if minimize:
        txt = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    else:
        txt = json.dumps(out, ensure_ascii=False, indent=2)

    st.subheader("生成された JSON")
    st.code(txt, language="json")
    st.download_button(
        "JSONをダウンロード",
        data=txt.encode("utf-8"),
        file_name="jyotish.json",
        mime="application/json",
    )

    with st.expander("計算仕様メモ（参考）", expanded=False):
        st.markdown(
            "- **キャッシュ方針**：計算結果（Asc/惑星/分割図）は `@st.cache_data`、"
            "初期設定（Ephemeris パス/サイデリアル設定）は `@st.cache_resource` を使用。"
            "（Streamlit 公式の推奨）"  # 参考
        )
        st.markdown("  参考: Streamlit Caching Overview / 新キャッシュAPI（cache_data/resource）")  # citations below
