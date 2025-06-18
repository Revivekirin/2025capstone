# data_loader.py

import json
import os
import re

import pandas as pd
import shodan
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
from shodan import APIError
from tqdm import tqdm

# ── 환경변수 로드 & Shodan 클라이언트 생성 ─────────────────────────
load_dotenv()
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")
shodan_api     = shodan.Shodan(SHODAN_API_KEY)

# ── SBERT 모델 로드 ────────────────────────────────────────────────
MODEL_NAME = "gtr-t5-base"
_model     = SentenceTransformer(MODEL_NAME)
_model.eval()

# ── Shodan API 호출 함수 ───────────────────────────────────────────
def load_shodan_api(
    query: str        = "apache",
    max_results: int  = 100
) -> pd.DataFrame:
    hosts = []
    try:
        for hit in shodan_api.search_cursor(query, minify=True):
            hosts.append({
                "ip":        hit.get("ip_str"),
                "org":       hit.get("org"),
                "latitude":  hit.get("location", {}).get("latitude"),
                "longitude": hit.get("location", {}).get("longitude"),
                "cve_list":  list(hit.get("vulns", {}).keys()) if isinstance(hit.get("vulns"), dict) else []
            })
            if len(hosts) >= max_results:
                break
    except APIError as e:
        st.error(f"Shodan API 오류: {e}")
    return pd.DataFrame(hosts).dropna(subset=["latitude","longitude"])

# ── 로컬 CVE DB + ATT&CK 병합 함수 ─────────────────────────────────
def load_cve_and_mitre(cve_csv: str, attack_xlsx: str):
    """로컬 CVE DB와 ATT&CK 매트릭스를 읽어 합칩니다."""
    df_cvedb = (
        pd.read_csv(cve_csv)
          .assign(
             mitre_match=lambda d: d["mitre_match"].apply(eval),
             technique_id=lambda d: d["mitre_match"].apply(lambda m: m["id"]),
             similarity=lambda d: d["mitre_match"].apply(lambda m: m["score"])
          )
          .dropna(subset=["cvss","technique_id","similarity"])
    )
    # 엑셀 읽어오기
    raw = pd.read_excel(attack_xlsx)
    # 컬럼 이름 소문자/공백 제거 기준으로 찾아내기
    cols = [c.strip() for c in raw.columns]
    id_col = next(c for c in cols if "technique id" in c.lower() or c.lower() == "id")
    name_col = next(c for c in cols if "technique name" in c.lower() or c.lower() == "name")
    desc_col = next(c for c in cols if "description" in c.lower())

    mitre_df = raw[[id_col, name_col, desc_col]].copy()
    mitre_df.columns = ["technique_id", "technique_name", "description"]
    mitre_df = mitre_df.dropna(subset=["technique_id", "technique_name", "description"])
    df_cvedb = df_cvedb.merge(mitre_df, on="technique_id", how="left")
    return df_cvedb, mitre_df

# ── 뉴스 요약 & 키워드 분류 함수 ────────────────────────────────────
def categorize_news(
    news_json: str,
    keywords: list[str],
    threshold: float = 0.3,
) -> pd.DataFrame:
    with open(news_json, encoding="utf-8") as f:
        recs = json.load(f)
    df = pd.DataFrame(recs)

    # 날짜 파싱
    if "date" in df.columns:
        src = "date"
    elif "published_at" in df.columns:
        src = "published_at"
    else:
        df["date"] = df["content"].str.extract(
            r"날짜[:：]\s*([A-Za-z]+ \d{1,2}, \s*\d{4})"
        )[0]
        src = "date"

    fmt = "%Y-%m-%d" if re.match(r"\d{4}-\d{2}-\d{2}", df[src].dropna().iloc[0]) else "%b %d, %Y"
    df["date"] = pd.to_datetime(df[src], format=fmt, errors="coerce")

    # summary 확보
    df["summary"] = (
        df.get("summary", df["content"].str[:200] + "...")
          .fillna(df["content"].str[:200] + "...")
    )

    # 키워드 임베딩 & 분류
    with torch.no_grad():
        kw_emb = _model.encode(keywords, convert_to_tensor=True, normalize_embeddings=True)
    cats, scores = [], []
    for txt in tqdm(df["summary"], desc="Embedding & Categorizing"):
        with torch.no_grad():
            emb = _model.encode(txt, convert_to_tensor=True, normalize_embeddings=True)
        cos = util.cos_sim(emb, kw_emb).squeeze(0)
        top_score, top_idx = float(torch.max(cos, dim=0)[0]), int(torch.max(cos, dim=0)[1])
        if top_score >= threshold:
            cats.append(keywords[top_idx]); scores.append(top_score)
        else:
            cats.append("Uncategorized");      scores.append(top_score)
    df["category"], df["category_score"] = cats, scores

    # 보기 좋은 날짜 문자열
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d").fillna("Unknown")
    return df

# ── 네 가지 데이터 한 번에 불러오기 ─────────────────────────────────
def load_all_data(
    *,
    shodan_query: str,
    shodan_limit: int,
    cve_csv: str,
    attack_xlsx: str,
    news_json: str,
    news_keywords: list[str],
    news_threshold: float = 0.3
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_shodan  = load_shodan_api(shodan_query, shodan_limit)
    df_cvedb, mitre_df = load_cve_and_mitre(cve_csv, attack_xlsx)
    df_news    = categorize_news(news_json, news_keywords, threshold=news_threshold)
    return df_shodan, df_cvedb, mitre_df, df_news