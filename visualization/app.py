# app.py

import os

import folium
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_ROOT = os.path.join(BASE_DIR, "data")

from data_loader import load_all_data

NEWS_KEYWORDS = [
    "ransomware","breach","malware","phishing","vulnerability",
    "attack","security","exploit","APT","botnet","zero-day",
    "rce","Trojan","data leak","DDoS"
]

@st.cache_data
def get_data():
    return load_all_data(
      shodan_query="product:apache",
      shodan_limit=200,
      cve_csv=os.path.join(DATA_ROOT, "shodan", "cvedb_shodan.csv"),
      attack_xlsx=os.path.join(DATA_ROOT, "enterprise-attack-v17.1.xlsx"),
      news_json=os.path.join(DATA_ROOT, "news_data.json"),
      news_keywords=NEWS_KEYWORDS,
      news_threshold=0.3
    )

df_shodan, df_cvedb, mitre_df, df_news = get_data()

# ── 사이드바 메뉴 ────────────────────────────────────────────────
st.sidebar.title("대시보드 메뉴")
menu = ["그룹 기반 분석","클러스터 기반 분석","News"]
if "menu" not in st.session_state:
    st.session_state.menu = menu[0]
for m in menu:
    if st.sidebar.button(m):
        st.session_state.menu = m

# ── 그룹 기반 분석 ────────────────────────────────────────────────
if st.session_state.menu == "그룹 기반 분석":
    st.title("Shodan 기반 위협 분석 — 그룹별 (org)")

    orgs = sorted(df_shodan["org"].fillna("Unknown").unique())
    sel  = st.selectbox("조직(org) 선택", orgs)
    grp  = df_shodan[df_shodan["org"] == sel]

    # ─────────────────────────────────────────────
    # 📍 새 지도(Globe/Plane) 토글 구간
    # ─────────────────────────────────────────────
    st.subheader("서버 위치")

    # 1) 사용자 토글
    map_mode = st.radio("🗺️ 지도 모드", ["Folium-Globe(2D)", "PyDeck-Orthographic"], horizontal=True)

    points = grp[["latitude", "longitude", "org"]].dropna()

    if map_mode == "PyDeck-Orthographic":  # 2-B 분기 시작
       # 0) ScatterplotLayer 정의
       layer = pdk.Layer(
           "ScatterplotLayer",
           data=points,
           get_position="[longitude, latitude]",
           get_fill_color="[200, 30, 0, 160]",
           get_radius=30000,
           pickable=True,
       )
       view_state = pdk.ViewState(
            latitude=float(points["latitude"].mean()),
            longitude=float(points["longitude"].mean()),
            zoom=0.8,
            min_zoom=0,
            max_zoom=4,
        )
       deck = pdk.Deck(
           layers=[layer],  # 정의한 layer 사용
            initial_view_state=view_state,
            views=[{"type": "OrthographicView"}],
            tooltip={"text": "{org}"},
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
        )
       
       st.pydeck_chart(deck)

# ─────────────────────────────────────────────

    # 지역별 서버 수 (region_full 없으면 org 기준으로)
    st.subheader("지역별 서버 수")
    if "region_full" in grp.columns:
        cnt = grp["region_full"]
    else:
        cnt = grp["org"].fillna("Unknown")
    rc = (
        cnt
        .value_counts()
        .rename_axis("region")
        .reset_index(name="count")
    )
    st.plotly_chart(px.bar(rc, x="region", y="count"), use_container_width=True)

# ── 클러스터 기반 분석 ────────────────────────────────────────────
elif st.session_state.menu == "클러스터 기반 분석":
    st.title("Shodan 기반 위협 분석 — 클러스터")
    # … (기존 클러스터 분석 코드) …

# ── News 슬라이드 ───────────────────────────────────────────────
else:
    st.title("📚 뉴스 요약 슬라이드")
    if "d_idx" not in st.session_state: st.session_state.d_idx = 0
    if "n_idx" not in st.session_state: st.session_state.n_idx = 0

    dates = sorted(df_news["date_str"].unique())
    sel_date = st.sidebar.selectbox("Date", dates, index=st.session_state.d_idx)
    if sel_date != dates[st.session_state.d_idx]:
        st.session_state.d_idx = dates.index(sel_date)
        st.session_state.n_idx = 0

    c1,_,c2 = st.columns([1,6,1])
    with c1:
        if st.button("⬅ 이전 날짜"):
            st.session_state.d_idx = max(0, st.session_state.d_idx-1)
            st.session_state.n_idx = 0
    with c2:
        if st.button("다음 날짜 ➡"):
            st.session_state.d_idx = min(len(dates)-1, st.session_state.d_idx+1)
            st.session_state.n_idx = 0

    today = dates[st.session_state.d_idx]
    st.header(f"📅 {today}")

    daily = df_news[df_news["date_str"] == today].reset_index(drop=True)
    if daily.empty:
        st.info("해당 일자 뉴스가 없습니다.")
    else:
        p1,_,p2 = st.columns([1,6,1])
        with p1:
            if st.button("◀ 이전 기사"):
                st.session_state.n_idx = (st.session_state.n_idx - 1) % len(daily)
        with p2:
            if st.button("다음 기사 ▶"):
                st.session_state.n_idx = (st.session_state.n_idx + 1) % len(daily)

        rec   = daily.iloc[st.session_state.n_idx]
        title = rec["title"]
        body  = rec["summary"]
        cat   = rec["category"]
        score = rec["category_score"]

        html = f"""
        <style>
          .flip-card {{ perspective:1000px; width:600px; height:260px; margin:auto; }}
          .flip-card-inner {{ position:relative; width:100%; height:100%;
                             transition:transform 0.8s; transform-style:preserve-3d; }}
          .flip-card:hover .flip-card-inner {{ transform:rotateY(180deg); }}
          .flip-card-front, .flip-card-back {{ position:absolute; width:100%; height:100%;
                                             backface-visibility:hidden;
                                             border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.15);
                                             padding:20px; background:white; }}
          .flip-card-back {{ transform:rotateY(180deg); }}
        </style>
        <div class="flip-card"><div class="flip-card-inner">
          <div class="flip-card-front">
            <h3>📰 {title}</h3>
            <p style="font-size:14px; line-height:1.4;">{body}</p>
          </div>
          <div class="flip-card-back">
            <h4>🔥 분류 키워드</h4>
            <p>{cat} ({score:.2f})</p>
          </div>
        </div></div>
        """
        components.html(html, height=300)
        st.caption(f"[{st.session_state.n_idx+1}/{len(daily)}]")