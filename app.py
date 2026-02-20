# -*- coding: utf-8 -*-
import os
import json
from datetime import date, datetime, time
import streamlit as st
import requests

# ============================================
# 設定
# ============================================
st.set_page_config(page_title="Jyotish Data Generator for AI", page_icon="🪷", layout="centered")
st.title("AI専用ヴェーダ占星術データ抽出ツール")

# APIベースURL（例：Streamlit Secrets または環境変数）
API_BASE = st.secrets.get("JYOTISH_API_BASE", os.getenv("JYOTISH_API_BASE", "http://localhost:9393"))

# 短縮表記マップ
PLANET_SHORT = {
    "Sun":"Su","Moon":"Mo","Mars":"Ma","Mercury":"Me","Jupiter":"Ju","Venus":"Ve","Saturn":"Sa","Rahu":"Ra","Ketu":"Ke",
    # APIが既に Su,Mo… ならそのまま通す
}
SIGN_NAMES = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_SHORT = {"Aries":"Ari","Taurus":"Tau","Gemini":"Gem","Cancer":"Can","Leo":"Leo","Virgo":"Vir",
              "Libra":"Lib","Scorpio":"Sco","Sagittarius":"Sag","Capricorn":"Cap","Aquarius":"Aqu","Pisces":"Pis"}

def sign_id_to_name(rashi_id:int) -> str:
    # jyotish-api の rashi は 1..12 想定。0/None ガードも付与
    idx = max(1, min(12, int(rashi_id))) - 1
    return SIGN_NAMES[idx]

# ============================================
# 1. 出生情報の入力
# ============================================
st.header("1. 出生情報の入力")
with st.container(border=True):
    c1, c2 = st.columns([1.5, 1])
    with c1:
        user_name = st.text_input("名前", value="Guest")
    with c2:
        gender = st.selectbox("性別", ["不明","男性","女性","その他"])

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
    col_op1, col_op2 = st.columns(2)

    with col_op1:
        node_ui = st.radio(
            "ノードの計算",
            ["Mean Node (平均)", "True Node (真位置)"],
            horizontal=True
        )
        node_mode = "true" if node_ui.startswith("True") else "mean"

        use_compact_planet = st.checkbox("惑星キー・サイン名を短縮（Sun→Su, Aries→Ari）", value=True)
        use_short_sd = st.checkbox("House/Sign/Degree キーも短縮（h/sg/deg）", value=True)
        minify_json = st.checkbox("出力するJSONを最小化（スペース・改行なし）", value=True)

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
        d60 = st.checkbox("D60 Shashtyamsa（すべて）", value=False)

# 送信ボタン
if st.button("AI向けJSONを生成", type="primary"):
    # --- varga パラメータ生成 ---
    vargas = []
    for key, flag in [("D1", d1), ("D3", d3), ("D4", d4), ("D7", d7), ("D9", d9), ("D10", d10),
                      ("D12", d12), ("D16", d16), ("D20", d20), ("D24", d24), ("D30", d30), ("D60", d60)]:
        if flag:
            vargas.append(key)
    if not vargas:
        vargas = ["D1"]
    varga_str = ",".join(vargas)

    # --- APIパラメータ組み立て ---
    # jyotish-api は GET /api/calculate をサポート
    # 例: ?latitude=...&longitude=...&year=...&month=...&day=...&hour=...&min=...&sec=...&time_zone=%2B09:00&varga=D1,D9&infolevel=basic,panchanga
    dt = datetime.combine(birth_date, time(h, m, s))
    tz_sign = "+" if tz >= 0 else "-"
    tz_h = int(abs(tz))
    tz_m = int(round((abs(tz) - tz_h) * 60))
    tz_str = f"{tz_sign}{tz_h:02d}:{tz_m:02d}"

    params = {
        "latitude": f"{lat:.6f}",
        "longitude": f"{lon:.6f}",
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "min": dt.minute,
        "sec": dt.second,
        "time_zone": tz_str,
        "dst_hour": 0,
        "dst_min": 0,
        "nesting": 0,
        "varga": varga_str,
        "infolevel": "basic,panchanga",
        "node": node_mode,  # ← 追加した改修で Mean/True の切り替え
    }

    # --- API呼び出し ---
    try:
        url = f"{API_BASE}/api/calculate"
        res = requests.get(url, params=params, timeout=40)
        res.raise_for_status()
        raw = res.json()  # APIのネイティブ応答

        # --- AI向けに再整形（短縮キーや名称付与） ---
        def compact_chart(api_chart: dict) -> dict:
            # 惑星・ラグナ・ハウス・varga をAI向けに正規化
            out = {
                "meta": {
                    "name": user_name,
                    "gender": gender,
                    "tz": tz_str,
                    "node": node_mode,      # mean|true
                    "varga": vargas,
                },
                "birth": {
                    "date": str(birth_date),
                    "time": f"{h:02d}:{m:02d}:{s:02d}",
                    "lat": lat, "lon": lon
                },
                "D": {}  # 分割図格納: D1, D9, ...
            }

            # ベース（D1相当）
            def normalize_block(block: dict, use_short=True):
                # graha: {"Su": {"rashi": 9, "degree": 8.98, ...}, ...}
                r_g = {}
                graha = block.get("graha", {})
                for k, v in graha.items():
                    # 既に Su/Mo... ならそのまま。フル名が来た場合は短縮へ。
                    key = PLANET_SHORT.get(k, k) if use_short else k
                    sg_name = sign_id_to_name(v.get("rashi")) if v.get("rashi") else None
                    if use_compact_planet and sg_name in SIGN_SHORT:
                        sg = SIGN_SHORT[sg_name]
                    else:
                        sg = sg_name
                    r_g[key] = {
                        ("sg" if use_short_sd else "sign"): sg,
                        ("deg" if use_short_sd else "degree"): v.get("degree"),
                        ("h" if use_short_sd else "house"): v.get("bhava") if v.get("bhava") else None,
                        "retro": v.get("retro", None),
                        "nak": v.get("nakshatra", {}).get("name") if v.get("nakshatra") else None,
                        "pada": v.get("nakshatra", {}).get("pada") if v.get("nakshatra") else None
                    }

                # lagna
                r_l = {}
                for lg_key, lg_val in (block.get("lagna") or {}).items():
                    sg_name = sign_id_to_name(lg_val.get("rashi")) if lg_val.get("rashi") else None
                    sg = SIGN_SHORT.get(sg_name, sg_name) if use_compact_planet else sg_name
                    r_l[lg_key] = {
                        ("sg" if use_short_sd else "sign"): sg,
                        ("deg" if use_short_sd else "degree"): lg_val.get("degree"),
                    }

                # house
                r_h = {}
                for num, hv in (block.get("bhava") or {}).items():
                    sg_name = sign_id_to_name(hv.get("rashi")) if hv.get("rashi") else None
                    sg = SIGN_SHORT.get(sg_name, sg_name) if use_compact_planet else sg_name
                    r_h[str(num)] = {
                        ("sg" if use_short_sd else "sign"): sg,
                        ("deg" if use_short_sd else "degree"): hv.get("degree"),
                    }

                return {"graha": r_g, "lagna": r_l, "house": r_h}

            chart = raw.get("chart", {})
            # D1
            out["D"]["D1"] = normalize_block(chart, use_short=True)
            # varga
            for vkey, vblock in (chart.get("varga") or {}).items():
                out["D"][vkey] = normalize_block(vblock, use_short=True)

            # panchanga
            p = chart.get("panchanga") or {}
            out["panchanga"] = {
                "tithi": p.get("tithi", {}).get("name"),
                "nakshatra": p.get("nakshatra", {}).get("name"),
                "yoga": p.get("yoga", {}).get("name"),
                "vara": p.get("vara", {}).get("name"),
                "karana": p.get("karana", {}).get("name"),
            }
            return out

        ai_json = compact_chart(raw.get("chart", {}))

        st.success("計算完了")
        st.caption("※計算は kunjara/jyotish（Swiss Ephemeris）ベースのAPIを利用しています。")

        # 表示
        if minify_json:
            js = json.dumps(ai_json, ensure_ascii=False, separators=(",", ":"))
        else:
            js = json.dumps(ai_json, ensure_ascii=False, indent=2)

        st.code(js, language="json")

        # ダウンロード
        st.download_button(
            "JSONをダウンロード",
            data=js.encode("utf-8"),
            file_name=f"{user_name}_jyotish_ai.json",
            mime="application/json",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
