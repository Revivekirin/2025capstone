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
    st.title("Shodan 기반 위협 분석 - 클러스터 기반")

    tech_pivot = (
        df_shodan.explode('cve_list')
        .merge(df_cvedb[['cve_id', 'technique_id']], left_on='cve_list', right_on='cve_id')
        .groupby(['group', 'technique_id']).size()
        .unstack(fill_value=0)
    )
    scaler = StandardScaler()
    tech_scaled = scaler.fit_transform(tech_pivot)

    distortions, silhouette_scores = [], []
    best_k, best_score = 2, -1
    K = range(2, min(11, len(tech_pivot)))
    for k in K:
        kmeans_model = KMeans(n_clusters=k, random_state=42).fit(tech_scaled)
        distortions.append(kmeans_model.inertia_)
        score = silhouette_score(tech_scaled, kmeans_model.labels_)
        silhouette_scores.append(score)
        if score > best_score:
            best_score, best_k = score, k

    if st.sidebar.checkbox("Elbow 차트 보기"):
        st.plotly_chart(px.line(x=list(K), y=distortions, markers=True, title="Elbow Curve"))
        st.plotly_chart(px.line(x=list(K), y=silhouette_scores, markers=True, title="Silhouette Score"))

    st.sidebar.markdown(f"**자동 선택된 클러스터 수: {best_k}**")
    kmeans = KMeans(n_clusters=best_k, random_state=42)
    cluster_labels = kmeans.fit_predict(tech_scaled)
    tech_pivot['cluster'] = cluster_labels

    reducer = umap.UMAP(random_state=42)
    embedding = reducer.fit_transform(tech_scaled)
    tech_pivot['umap_x'] = embedding[:, 0]
    tech_pivot['umap_y'] = embedding[:, 1]

    # Index를 컬럼으로 복원
    tech_pivot_reset = tech_pivot.reset_index()

    st.subheader("클러스터별 그룹 위치 (UMAP 시각화)")
    fig_umap = px.scatter(
        tech_pivot_reset,
        x='umap_x',
        y='umap_y',
        color='cluster',
        hover_data=['group'],

    )
    st.plotly_chart(fig_umap)


    df_shodan_clustered = df_shodan.merge(tech_pivot[['cluster']].reset_index(), on='group', how='left')
    selected_clusters = st.multiselect("분석할 클러스터 선택",
                                        sorted(df_shodan_clustered['cluster'].dropna().unique()),
                                        default=sorted(df_shodan_clustered['cluster'].dropna().unique()))

    # st.subheader("클러스터별 그룹 목록")
    # all_group_counts = df_shodan_clustered[df_shodan_clustered['cluster'].isin(selected_clusters)]
    # st.dataframe(all_group_counts.groupby(['group', 'cluster']).size().reset_index(name='server_count'))

    st.subheader("클러스터별 Technique 분포")
    df_exploded = df_shodan_clustered[df_shodan_clustered['cluster'].isin(selected_clusters)].explode('cve_list')
    merged = df_exploded.merge(df_cvedb[['cve_id', 'technique_id']], left_on='cve_list', right_on='cve_id')
    merged = merged.merge(mitre_df[['technique_id', 'technique_name', 'description']], on='technique_id', how='left')
    tech_count = merged.groupby(['cluster', 'technique_id', 'technique_name', 'description']).size().reset_index(name='count')
    fig_tech = px.bar(tech_count, x='technique_id', y='count', color='cluster', facet_col='cluster', hover_data=['technique_name'])
    st.plotly_chart(fig_tech, use_container_width=True)

    st.subheader("클러스터별 TTP 설명 요약 (Gemini AI)")

    top_ttps = tech_count.groupby('cluster').apply(lambda d: d.sort_values('count', ascending=False).head(5)).reset_index(drop=True)

    for clus in sorted(top_ttps['cluster'].unique()):
        st.markdown(f"### 🔹 클러스터 {clus}")
        top_df = top_ttps[top_ttps['cluster'] == clus]

        # TTP 설명 하나로 합치기
        description_text = ". ".join(
            f"{row['technique_name']} ({row['technique_id']}): {row['description']}" for _, row in top_df.iterrows()
        )

        # 프롬프트 구성
        prompt = f"""
    아래는 사이버 공격 클러스터 {clus}에서 자주 나타나는 MITRE ATT&CK TTP 설명입니다:

    {description_text}

    이 클러스터의 위협 행위 특성과 관련 랜섬웨어 그룹의 공격 전략을 기반으로 다음을 요약해 주세요:
    - 어떤 공격 유형이 포함되는가 (초기 침입, lateral movement 등)
    - 특징적인 TTP 조합이 의미하는 위협 유형
    - 관련 랜섬웨어 그룹 사례 예시가 있다면

    요약으로 제시해 주세요.
        """

        if st.button(f"Gemini로 요약 생성하기 - 클러스터 {clus}", key=f"gemini_btn_{clus}"):
            with st.spinner("Gemini 모델로 요약 생성 중..."):
                try:
                    summary = summarize_with_gemini(prompt)
                    st.success("요약 완료")
                    st.markdown(f"**LLM 분석 결과:**\n\n{summary}")
                except Exception as e:
                    st.error(f"Gemini API 호출 실패: {e}")
                    st.markdown("### Fallback: TTP 설명 요약 (수동 출력)")
                    for _, row in top_df.iterrows():
                        st.markdown(f"- **{row['technique_name']} ({row['technique_id']})**: {row['description']}")

    
    st.subheader("클러스터별 Top TTP 레이다 차트")
    top_ttp_ids = tech_count.groupby('technique_id')['count'].sum().nlargest(8).index.tolist()
    pivot_radar = tech_count[tech_count['technique_id'].isin(top_ttp_ids)].pivot(index='cluster', columns='technique_id', values='count').fillna(0)
    fig_radar = go.Figure()
    for cluster in pivot_radar.index:
        fig_radar.add_trace(go.Scatterpolar(
            r=pivot_radar.loc[cluster].values,
            theta=top_ttp_ids,
            fill='toself',
            name=f'Cluster {cluster}'
        ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), title="Radar Chart of TTPs")
    st.plotly_chart(fig_radar)

    with st.expander("전체 TTP 설명 테이블"):
        st.dataframe(mitre_df[['technique_id', 'technique_name', 'description']].drop_duplicates().sort_values('technique_id'))
