"""
# extract_url.py에서 수집한 IP 주소를 기반으로 Shodan API를 호출하여 정보를 가져옵니다.
# Shodan API를 사용하여 IP 주소에 대한 정보를 수집하고, 주요 feature를 추출하여 CSV 파일로 저장하는 스크립트
"""
import os
import pandas as pd
import subprocess
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv


# .env 파일 로드
load_dotenv()
api_key = os.getenv("SHODAN_API_KEY")
if not api_key:
    raise ValueError("API 키가 .env 파일에서 로드되지 않았습니다.")

# CSV 파일 경로 설정
today_str = datetime.now().strftime("%Y%m%d")
# today_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
csv_path = f"urls_with_groups_ip_{today_str}.csv"

# 기존 CSV 파일 불러오기
df = pd.read_csv(csv_path)

# 결과를 저장할 리스트
results = []

# 주요 feature 추출 함수
def extract_features(data):
    def get_nested(d, *keys):
        for key in keys:
            d = d.get(key, {})
        return d if d else None

    features = {
        "product": data.get("product", []),
        "version": data.get("version", []),
        "cpe": data.get("cpe", []),
        "cpe23": data.get("cpe23", []),
        "components": list(get_nested(data, "http", "components").keys()) if get_nested(data, "http", "components") else [],
        "ssh_key": get_nested(data, "ssh", "key"),
        "ssh_kex": get_nested(data, "ssh", "kex", "kex_algorithms"),
        "ssh_mac": get_nested(data, "ssh", "kex", "mac_algorithms"),
        "ssh_cipher": get_nested(data, "ssh", "cipher"),
        "ssl_ja3s": get_nested(data, "ssl", "ja3s"),
        "ssl_jarm": get_nested(data, "ssl", "jarm"),
        "ssl_fingerprint": get_nested(data, "ssl", "cert", "fingerprint", "sha256"),
        "hostnames": data.get("hostnames"),
        "domains": data.get("domains"),
        "vulns": data.get("vulns"),
        "tags": data.get("tags"),
        "server": get_nested(data, "http", "server"),
        "asn": data.get("asn"),
        "org": data.get("org"),
        "isp": data.get("isp"),
        "country_code": data.get("country_code"),
        "region_code": data.get("region_code"),
        "ssl_issuer": get_nested(data, "ssl", "cert", "issuer"),
        "ssl_subject": get_nested(data, "ssl", "cert", "subject")
    }

    # 리스트 및 dict 값을 문자열로 변환
    for k, v in features.items():
        if isinstance(v, list):
            features[k] = ", ".join(map(str, v))
        elif isinstance(v, dict):
            features[k] = json.dumps(v)
    return features


# 각 IP에 대해 curl 실행 및 데이터 수집
for index, row in df.iterrows():
    shodan_ip = row['ip_address']
    if shodan_ip == "NO_IP_FOUND":
        results.append({})
        continue

    try:
        cmd = f'curl -s "https://api.shodan.io/shodan/host/{shodan_ip}?key={api_key}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        data = json.loads(result.stdout)

        merged_data = {}
        for item in data.get("data", []):
            merged_data.update(item)
        merged_data.update({k: v for k, v in data.items() if k != "data"})

        features = extract_features(merged_data)
        results.append(features)
        print(f"{shodan_ip} 처리 완료")

    except Exception as e:
        print(f"{shodan_ip} 처리 실패: {e}")
        results.append({})


# 결과 병합
feature_df = pd.DataFrame(results)
merged_df = pd.concat([df, feature_df], axis=1)
merged_df.to_csv(csv_path, index=False, encoding='utf-8')
print(f"[✓] 분석 결과 저장 완료: {csv_path}")