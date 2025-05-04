"""
HTML 파싱 + group 매칭 + URL 추출 + IP 주소 조회
"""
import os
import csv
import json
import re
import subprocess
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timedelta

# 경로 설정
html_dir = Path("~/downloads")
onion_json = Path("~/downloads/onion_list.json")
today_str = datetime.now().strftime("%Y%m%d")
# today_str = today_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
output_csv = f"urls_with_groups_ip_{today_str}.csv"

# JSON 로딩: fqdn → group 맵핑
with open(onion_json, "r", encoding="utf-8") as f:
    fqdn_to_group = {
        entry["fqdn"].replace("http://", "").replace("https://", ""): entry["group"]
        for entry in json.load(f)
    }

# 유틸: 도메인 추출 함수
def extract_domain(raw_url):
    url = re.sub(r"https?://", "", raw_url)
    url = re.sub(r"^www\.", "", url)
    return url.strip().split('/')[0]

# 유틸: IP 조회 함수
def get_ip_from_dig(domain):
    try:
        dig_result = subprocess.check_output(["dig", "+short", domain], encoding='utf-8')
        for line in dig_result.strip().split("\n"):
            if re.match(r"\d+\.\d+\.\d+\.\d+", line):
                return line
        return "NO_IP_FOUND"
    except subprocess.CalledProcessError:
        return "DIG_ERROR"

# 결과 저장
all_entries = []

# HTML 파일 순회
for html_file in html_dir.glob("*.html"):
    domain_part = html_file.stem.split("_")[0]
    fqdn_full = domain_part + ".onion"
    matched_group = fqdn_to_group.get(fqdn_full, "unknown")

    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        text = soup.get_text(separator="\n")
        matches = re.findall(r"(https?://)?(www\.[^\s<>\"]+|[^\s<>\"]+\.com)", text)

        for match in matches:
            url = "".join(match).strip()
            if "." in url and len(url) > 8:
                domain = extract_domain(url)
                ip = get_ip_from_dig(domain)
                print(f"[+] {domain} → {ip}")
                all_entries.append((html_file.name, matched_group, url, ip))

# CSV 저장
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["html_file", "group", "url", "ip_address"])
    writer.writerows(all_entries)

print(f"\n[✓] 총 {len(all_entries)}개 URL을 {output_csv}에 IP 포함하여 저장했습니다.")
