# --- 1. 出生情報の入力 ---
st.header("1. 出生情報の入力")
with st.container(border=True):

    col_name, col_gen = st.columns(2)
    with col_name:
        user_name = st.text_input("名前", value="Guest")
    with col_gen:
        gender = st.selectbox("性別（表示は日本語・出力は英語）",
                              ["不明", "男性", "女性", "その他"])

    # 出生日
    birth_date = st.date_input("出生日", value=date(1990, 1, 1), min_value=date(1900, 1, 1))

    # 出生時刻（時・分・秒をドロップダウン化）
    st.write("出生時刻（ドロップダウン）")
    col_h, col_m, col_s = st.columns(3)
    with col_h:
        h = st.selectbox("時", list(range(0, 24)), index=12)
    with col_m:
        m = st.selectbox("分", list(range(0, 60)), index=0)
    with col_s:
        s = st.selectbox("秒", list(range(0, 60)), index=0)

    # 緯度・経度（手入力）
    st.write("出生地（緯度・経度を手入力）")
    col_lat, col_lon = st.columns(2)
    with col_lat:
        lat = st.number_input("緯度（北緯+／南緯-）", value=35.0000, format="%.6f")
    with col_lon:
        lon = st.number_input("経度（東経+／西経-）", value=135.0000, format="%.6f")

    # タイムゾーン（ユーザーがUTCオフセットを入力）
    tz = st.number_input("UTCオフセット（例：日本 = +9.0）", value=9.0, step=0.5, format="%.1f")
``
