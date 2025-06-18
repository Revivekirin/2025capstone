import streamlit as st
import pandas as pd
import os
import ast
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import umap.umap_ as umap
import requests
import json
from google import genai
from dotenv import load_dotenv

# ----------------- 경로 설정 ------------------------
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shodan_data_path = os.path.join(project_root, "data", "shodan", "shodan_data.csv")
cve_db_path = os.path.join(project_root, "data", "shodan", "cvedb_shodan.csv")
attack_matrix_path = os.path.join(project_root, "data", "enterprise-attack-v17.1.xlsx")

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def summarize_with_gemini(prompt):
    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    
    return response.text


# ----------------- 데이터 로드 및 전처리 -----------------
@st.cache_data
def load_data():
    df_shodan = pd.read_csv(shodan_data_path)
    df_shodan = df_shodan.dropna(subset=['latitude', 'longitude'])
    df_shodan['cve_list'] = df_shodan['cve_list'].apply(eval)
    df_shodan['region_full'] = df_shodan['country_code'] + " - " + df_shodan['region_code']

    df_cvedb = pd.read_csv(cve_db_path)
    df_cvedb['mitre_match'] = df_cvedb['mitre_match'].apply(ast.literal_eval)
    df_cvedb['technique_id'] = df_cvedb['mitre_match'].apply(lambda d: d.get('id'))
    df_cvedb['similarity'] = df_cvedb['mitre_match'].apply(lambda d: d.get('score'))
    df_cvedb = df_cvedb.dropna(subset=['cvss', 'technique_id', 'similarity'])

    mitre_df = pd.read_excel(attack_matrix_path)
    for col in mitre_df.columns:
        if col.strip().lower() in ['id', 'technique id']:
            mitre_df.rename(columns={col: 'technique_id'}, inplace=True)
        elif col.strip().lower() in ['name', 'technique name']:
            mitre_df.rename(columns={col: 'technique_name'}, inplace=True)
        elif col.strip().lower() == 'description':
            mitre_df.rename(columns={col: 'description'}, inplace=True)

    mitre_df = mitre_df[['technique_id', 'technique_name', 'description']].dropna()
    df_cvedb = df_cvedb.merge(mitre_df, on='technique_id', how='left')

    return df_shodan, df_cvedb, mitre_df

# ----------------- Streamlit 사이드바 -----------------
st.sidebar.title("대시보드 메뉴")

# 세션 상태 초기화
if "menu_option" not in st.session_state:
    st.session_state.menu_option = "그룹 기반 분석"

# 버튼 스타일 공통 적용 (가로 폭 100%, 높이 40px 등)
button_style = """
<style>
.sidebar-button {
    display: block;
    width: 100%;
    padding: 0.5rem;
    text-align: center;
    font-size: 16px;
    margin-bottom: 8px;
    background-color: #f0f2f6;
    border: 1px solid #ccc;
    border-radius: 5px;
    cursor: pointer;
}
.sidebar-button:hover {
    background-color: #e0e0e0;
}
</style>
"""

# 삽입
st.markdown(button_style, unsafe_allow_html=True)

# 버튼 UI 구현
if st.sidebar.button("그룹 기반 분석", key="btn_group"):
    st.session_state.menu_option = "그룹 기반 분석"
if st.sidebar.button("클러스터 기반 분석", key="btn_cluster"):
    st.session_state.menu_option = "클러스터 기반 분석"

# 현재 선택된 메뉴
menu_option = st.session_state.menu_option


# ----------------- 데이터 로딩 -----------------
df_shodan, df_cvedb, mitre_df = load_data()

cve_to_ttp = df_cvedb.set_index('cve_id')['technique_name'].to_dict()
df_shodan['cve_summary'] = df_shodan['cve_list'].apply(lambda cves: ', '.join(cves[:3]) + ('...' if len(cves) > 3 else ''))
df_shodan['ttp_summary'] = df_shodan['cve_list'].apply(
    lambda cves: ', '.join({cve_to_ttp[cve] for cve in cves if cve in cve_to_ttp})
)
df_shodan['tooltip_info'] = df_shodan.apply(
    lambda row: f"Group: {row['group']}\nDomain: {row['domain']}\nCVE: {row['cve_summary']}\nTTP: {row['ttp_summary']}", axis=1
)

# ----------------- 그룹 기반 분석 -----------------
if menu_option == "그룹 기반 분석":
    st.title("Shodan 기반 위협 분석 - 그룹별 시각화")

    group_list = sorted(df_shodan['group'].unique())
    selected_group = st.selectbox("분석할 그룹 선택", group_list)
    group_df = df_shodan[df_shodan['group'] == selected_group]
    group_cves = sum(group_df['cve_list'], [])
    group_cvedb = df_cvedb[df_cvedb['cve_id'].isin(group_cves)].copy()

    st.subheader("전체 서버 위치 및 위협 정보")
    layer = pdk.Layer("ScatterplotLayer", df_shodan,
                      get_position='[longitude, latitude]', get_fill_color='[200, 30, 0, 160]',
                      get_radius=50000, pickable=True)
    view_state = pdk.ViewState(latitude=df_shodan['latitude'].mean(),
                               longitude=df_shodan['longitude'].mean(), zoom=1, pitch=0)
    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{tooltip_info}"})
    st.pydeck_chart(r)

    st.subheader("지역별 서버 수")
    region_count = group_df['region_full'].value_counts().reset_index()
    region_count.columns = ['region_full', 'server_count']
    st.plotly_chart(px.bar(region_count, x='region_full', y='server_count'), use_container_width=True)

    st.subheader("🛡️ ATT&CK Technique 분포 (TTP ID 기준)")
    tech_count = group_cvedb.groupby(['technique_id', 'technique_name', 'description']).size().reset_index(name='count')
    fig = px.bar(tech_count, x='technique_id', y='count', hover_data=['technique_name'],
                 title=f"{selected_group}의 ATT&CK Technique 매칭 분포 (TTP ID 기준)",
                 labels={'technique_id': 'TTP ID', 'count': 'Matching Count'})
    fig.update_traces(marker_color='indianred',
                      hovertemplate='<b>TTP ID:</b> %{x}<br><b>Count:</b> %{y}<br><b>Name:</b> %{customdata[0]}')
    st.plotly_chart(fig, use_container_width=True)

# ----------------- 클러스터 기반 분석 -----------------
else:
    st.title("Shodan 기반 위협 분석 - 그룹 단위 TTP 분석")

    group_list = sorted(df_shodan['group'].unique())
    selected_groups = st.multiselect("분석할 그룹 선택", group_list, default=group_list)

    df_filtered = df_shodan[df_shodan['group'].isin(selected_groups)].explode('cve_list')
    merged = df_filtered.merge(df_cvedb[['cve_id', 'technique_id']], left_on='cve_list', right_on='cve_id')
    merged = merged.merge(mitre_df[['technique_id', 'technique_name', 'description']], on='technique_id', how='left')

    # 그룹별 주요 TTP 요약
    st.subheader("그룹별 주요 TTP 설명 요약 (Gemini AI)")

    top_ttps = merged.groupby(['group', 'technique_id', 'technique_name', 'description']).size().reset_index(name='count')
    top_ttps = top_ttps.groupby('group').apply(lambda d: d.sort_values('count', ascending=False).head(5)).reset_index(drop=True)

    for group in selected_groups:
        st.markdown(f"### 🔹 그룹: {group}")
        top_df = top_ttps[top_ttps['group'] == group]

        # 설명 합치기
        description_text = ". ".join(
            f"{row['technique_name']} ({row['technique_id']}): {row['description']}" for _, row in top_df.iterrows()
        )

        # 프롬프트
        prompt = f"""
    다음은 공격 그룹 '{group}'에서 자주 나타나는 MITRE ATT&CK 기술(TTP) 설명입니다:

    {description_text}

    이 그룹의 전반적인 공격 특성과 전략을 다음과 같이 요약해 주세요:
    - 주요 공격 단계 (예: 초기 침입, lateral movement 등)
    - 위협 시나리오의 일반적 특징
    - 관련 랜섬웨어 그룹이 있다면 예시 제시

    5줄 이내로 간결히 정리해 주세요.
        """

        if st.button(f"Gemini 요약 생성 - {group}", key=f"gemini_btn_{group}"):
            with st.spinner("Gemini로 요약 생성 중..."):
                try:
                    summary = summarize_with_gemini(prompt)
                    st.success("요약 완료")
                    st.markdown(f"**LLM 분석 결과:**\n\n{summary}")
                except Exception as e:
                    st.error(f"Gemini 호출 실패: {e}")
                    st.markdown("### Fallback 요약")
                    for _, row in top_df.iterrows():
                        st.markdown(f"- **{row['technique_name']} ({row['technique_id']})**: {row['description']}")




#------ 클러스터별 TTP 분석 레이다 차트 ------
    # 1. 그룹별 TTP count 계산
    tech_count = merged.groupby(['group', 'technique_id', 'technique_name', 'description']) \
                    .size().reset_index(name='count')

    # 2. Top TTP 선정
    top_ttp_ids = tech_count.groupby('technique_id')['count'].sum().nlargest(8).index.tolist()

    # 3. 피벗 테이블: group vs TTP
    pivot_radar = tech_count[
        tech_count['technique_id'].isin(top_ttp_ids)
    ].pivot(index='group', columns='technique_id', values='count').fillna(0)

    # 4. 레이다 차트 시각화
    fig_radar = go.Figure()
    for group in pivot_radar.index:
        fig_radar.add_trace(go.Scatterpolar(
            r=pivot_radar.loc[group].values,
            theta=top_ttp_ids,
            fill='toself',
            name=f'Group: {group}'
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, showticklabels=True)),
        title="Radar Chart of Top TTPs per Group"
    )
    st.plotly_chart(fig_radar)


