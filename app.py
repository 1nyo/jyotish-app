# app.py
import json
from datetime import date, datetime
import streamlit as st
import swisseph as swe

# ---- calc modules ----
from calc.ephemeris import setup_sidereal, jd_ut_from_local, ayanamsa_deg, asc_sidereal, planet_sidereal_longitudes
from calc.d1 import build_d1
from calc.d9 import build_d9
from calc.d20 import build_d20
from calc.d60 import build_d60
from calc.validators import prune_and_validate

# ----------------------
# Helpers
# ----------------------
def format_tz(tz: float) -> str:
    # "UTC+9" / "UTC-5.5"
    sgn = "+" if tz >= 0 else "-"
    val = abs(tz)
    if abs(val - int(val)) < 1e-9:
        return f"UTC{sgn}{int(val)}"
    return f"UTC{sgn}{val:.1f}"

def deg_to_dms_str(deg: float, always_sign_minus=False) -> str:
    # 23.565 -> "-23:33:54"
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

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

# ----------------------
# Streamlit UI
# ----------------------
st.set_page_config(page_title="AI用 Jyotish データ作成ツール", layout="wide")
st.title("AI用 Jyotish データ作成ツール")

# ============================================
# 1. 出生情報の入力
# ============================================
st.header("1. 出生情報の入力")
with st.container(border=True):
    c1, c2 = st.columns([1.5, 1])
    with c1:
        user_name = st.text_input("名前", value="Guest")
        location_label = st.text_input("出生地（任意ラベル）", value="Unknown")
    with c2:
        gender = st.selectbox("性別", ["不明","男性","女性","その他"], index=0)

    # 日付・時刻
    st.write("出生日・時刻（24時間制）")
    d1c, d2c, d3c, d4c = st.columns([1.8, 1, 1, 1])
    with d1c:
        birth_date = st.date_input("出生日", value=date(1990,1,1))
    with d2c:
        h = st.selectbox("時", list(range(0,24)), index=12)
    with d3c:
        m = st.selectbox("分", list(range(0,60)), index=0)
    with d4c:
        s = st.selectbox("秒", list(range(0,60)), index=0)

    # 緯度・経度・UTC offset
    st.write("出生地（緯度・経度・UTCオフセット）初期値は東京")
    g1, g2, g3 = st.columns([1, 1, 1])
    with g1:
        lat = st.number_input("緯度（北緯+／南緯-）", value=35.68000, format="%.6f")
    with g2:
        lon = st.number_input("経度（東経+／西経-）", value=139.75000, format="%.6f")
    with g3:
        tz = st.number_input("UTCオフセット", value=9.0, step=0.5, format="%.1f")

# ============================================
# 2. 出力方法の設定
# ============================================
st.header("2. 出力方法の設定")
with st.expander("クリックで展開", expanded=True):
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        node_type = st.radio("ノードの計算", ["True Node（真）","Mean Node（平均）"], index=0)
        ck_mode = st.radio("Chara Karaka", ["7（Rahu除外）","8（Rahu含む）"], index=0)
        include_lordship = st.checkbox("支配関係を出力に含む", value=True)
    with col2:
        include_d1 = st.checkbox("D1 Rashi（基本）", value=True)
        include_d9 = st.checkbox("D9 Navamsa（本質層）", value=True)
        include_d20 = st.checkbox("D20 Vimsamsa（精神性、宗教）", value=False)
        include_d60 = st.checkbox("D60 Shashtyamsa（深層カルマ）", value=False)
    with col3:
        minimize = st.checkbox("出力するJSONを最小化（スペース・改行なし）", value=True)
        ephe_path = st.text_input("Swiss Ephemeris ファイルパス（空で内蔵）", value="")

# 送信ボタン
go = st.button("AI向けJSONを生成", type="primary")

# ============================================
# 実行
# ============================================
if go:
    # Swiss path
    try:
        swe.set_ephe_path(ephe_path if ephe_path.strip() else None)
    except Exception:
        swe.set_ephe_path(None)

    # Sidereal (Lahiri ICRC → fallback Lahiri)
    setup_sidereal("Lahiri_ICRC")  # ICRC が無ければモジュール内で Lahiri にフォールバック

    # 時刻
    h_float = int(h) + int(m)/60.0 + int(s)/3600.0
    jd_ut = jd_ut_from_local(birth_date.year, birth_date.month, birth_date.day, h_float, tz)

    # Asc（サイデリアル, Whole Sign）, 惑星（サイデリアル黄経＋速度）
    asc = asc_sidereal(jd_ut, lat, lon)
    node_flag = "True" if node_type.startswith("True") else "Mean"
    planets = planet_sidereal_longitudes(jd_ut, node_flag)

    # Ayanamsa（Lahiri ICRC の値を表示用に）
    aya = ayanamsa_deg(jd_ut)  # degrees
    aya_str = deg_to_dms_str(aya, always_sign_minus=True)  # "-23:33:56" 風

    # meta
    meta = {
        "name": user_name,
        "birth": f"{birth_date.isoformat()} {int(h):02d}:{int(m):02d}",
        "timezone": format_tz(tz),
        "latitude": f"{lat:.2f}",
        "longitude": f"{lon:.2f}",
        "location": location_label,
        "ayanamsa": f"Lahiri ICRC {aya_str}",
        "calculation_model": "Drik Siddhanta",
        "node_type": "True" if node_flag == "True" else "Mean",
        "house_system": "Whole Sign"
    }

    # オプション
    opts = {
        "ck_mode": "8" if ck_mode.startswith("8") else "7",
        "include_lordship": include_lordship
    }

    # 構築
    out = {"meta": meta}

    # D1
    if include_d1:
        D1 = build_d1(asc, planets, opts)
    else:
        D1 = None

    # D9
    if include_d9:
        D9 = build_d9(asc, planets)
    else:
        D9 = None

    # Karakamsa を D1 に注入（AK の D9 サイン）
    if D1 is not None and D9 is not None:
        try:
            ak = D1.get("jaimini", {}).get("AK")
            if ak:
                karakamsa_sign = D9["planets"][ak]["sign"]
                D1.setdefault("jaimini", {})["karakamsa_sign"] = karakamsa_sign
        except Exception:
            pass

    if include_d1:
        out["D1"] = D1
    if include_d9:
        out["D9"] = D9
    if include_d20:
        out["D20"] = build_d20(asc, planets)
    if include_d60:
        out["D60"] = build_d60(asc, planets)

    # バリデーション＆null除去
    out = prune_and_validate(out)

    # 表示
    if minimize:
        txt = json.dumps(out, ensure_ascii=False, separators=(',',':'))
    else:
        txt = json.dumps(out, ensure_ascii=False, indent=2)

    st.subheader("生成された JSON")
    st.code(txt, language="json")

    # ダウンロード
    st.download_button("JSONをダウンロード", data=txt.encode('utf-8'), file_name="jyotish.json", mime="application/json")

    # 参考メモ
    with st.expander("計算仕様メモ（参考）", expanded=False):
        st.markdown(
            "- **Tithi/Paksha**：太陽−月の地心黄経差を 12° 刻みで区分。1–15＝Shukla、16–30＝Krishna、15＝Purnima、30＝Amavasya。"
            "（一般的なパンチャーンガの定義）"  # 参考
        )
        st.markdown("  出典例：W3HTech Tithi 定義／Freedom Vidya 解説。")  # citations below
        st.markdown(
            "- **Whole Sign houses**：Swiss Ephemeris `houses_ex(..., FLG_SIDEREAL, 'W')` を使用。"
        )
        st.markdown(
            "  出典例：Swiss Ephemeris docs（house methods / extended functions）。"
        )
