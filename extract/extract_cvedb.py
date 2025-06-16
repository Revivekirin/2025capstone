import pandas as pd
import requests
import numpy as np
import time
import ast
from tqdm import tqdm
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

from mitre.matcher import calculate_mire_embedding
from nlp.embedder_st import get_embedding_st


def parse_cve_list(val):
    try:
        if pd.isna(val):
            return []
        parsed = ast.literal_eval(val) if isinstance(val, str) else val
        return [cve for cve in parsed if isinstance(cve, str) and cve.startswith("CVE-")]
    except Exception:
        return []

def extract_all_unique_cves(shodan_data_path):
    df = pd.read_csv(shodan_data_path)
    df['parsed_cve_list'] = df['cve_list'].apply(parse_cve_list)

    all_cves = set()
    for cves in df['parsed_cve_list']:
        all_cves.update(cves)
    return sorted(list(all_cves))

def get_cvedb_details_shodan(cve_id):
    url = f"https://cvedb.shodan.io/cve/{cve_id}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            return {
                "cve_id": data.get("cve_id"),
                "summary": data.get("summary"),
                "cvss": data.get("cvss"),
                "cvss_v2": data.get("cvss_v2"),
                "cvss_v3": data.get("cvss_v3"),
                "epss": data.get("epss"),
                "ranking_epss": data.get("ranking_epss"),
                "kev": data.get("kev"),
                "ransomware_campaign": data.get("ransomware_campaign"),
                "propose_action": data.get("propose_action"),
                "cpes": data.get("cpes", []),
                "published_time": data.get("published_time")
            }
    except Exception as e:
        return {"cve_id": cve_id, "error": str(e)}
    return {"cve_id": cve_id, "error": "No response"}

def update_cvedb_from_shodan(shodan_data_path, output_dir_path):
    cvedb_path = Path(output_dir_path)
    existing_cvedb_df = pd.DataFrame()

    if cvedb_path.exists():
        try:
            existing_cvedb_df = pd.read_csv(cvedb_path)
            print(f"[Info] 기존 CVE DB 로드 완료: {len(existing_cvedb_df)}개 항목")
        except Exception as e:
            print(f"[경고] 기존 CVE DB 파일 로드 실패: {e}")

    existing_cves = set(existing_cvedb_df['cve_id'].dropna()) if 'cve_id' in existing_cvedb_df.columns else set()
    all_cves = extract_all_unique_cves(shodan_data_path)
    new_cves = sorted(list(set(all_cves) - existing_cves))
    print(f"[Info] 새롭게 수집할 CVE 수: {len(new_cves)}")

    results = []
    for cve in tqdm(new_cves, desc="Fetching CVE details from Shodan"):
        result = get_cvedb_details_shodan(cve)
        results.append(result)
        time.sleep(1.2)

    if results:
        df_new = pd.DataFrame(results)
        df_combined = pd.concat([existing_cvedb_df, df_new], ignore_index=True)
        df_combined.to_csv(cvedb_path, index=False)
        print(f"[완료] cvedb_shodan.csv에 {len(results)}개 CVE 정보가 추가되었습니다.")
    else:
        print("새로 수집할 CVE 정보가 없습니다.")

def match_cves_to_mitre(cvedb_csv_path, mitre_excel_path):
    df_cvedb = pd.read_csv(cvedb_csv_path)

    if 'mitre_matches' in df_cvedb.columns and df_cvedb['mitre_matches'].notna().all():
        print("모든 항목에 이미 mitre_matches가 존재합니다. 매핑을 건너뜁니다.")
        return

    mitre_df = pd.read_excel(mitre_excel_path)
    techniques = list(zip(mitre_df['ID'], mitre_df['description'].fillna("")))

    mitre_embeddings_array, valid_techniques = calculate_mire_embedding(techniques)
    if mitre_embeddings_array is None:
        print("No valid MIRE embeddings found. Skipping.")
        return

    cve_summaries = df_cvedb[['cve_id', 'summary']].fillna("").to_dict(orient='records')
    mitre_results = {}

    for entry in tqdm(cve_summaries):
        cve_id = entry['cve_id']
        content = entry['summary']

        if not content.strip():
            mitre_results[cve_id] = None
            continue

        emb = get_embedding_st(content)
        if emb is None:
            mitre_results[cve_id] = None
            continue

        similarities = cosine_similarity([emb], mitre_embeddings_array)[0]
        best_idx = np.argmax(similarities)

        matched_id, matched_name = valid_techniques[best_idx]
        match_score = float(similarities[best_idx])

        mitre_results[cve_id] = {
            "id": matched_id,
            "name": matched_name,
            "score": match_score,
        }

    df_cvedb['mitre_match'] = df_cvedb['cve_id'].apply(lambda x: mitre_results.get(x))
    df_cvedb.to_csv(cvedb_csv_path, index=False)
    print(f"MITRE 매핑 결과가 열로 추가되어 저장되었습니다: {cvedb_csv_path}")
