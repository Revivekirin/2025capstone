import os
import csv
import json
import re
import subprocess
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.getenv("BASE_DIR") 
ONION_LIST_DIR = os.getenv("ONION_JSON_PATH ")

html_dir = Path(BASE_DIR)

onion_json = Path(ONION_LIST_DIR )
today_str = datetime.now().strftime("%Y%m%d")
output_csv_path = Path(f"urls_with_groups_ip_{today_str}.csv")


# 유틸: 도메인 추출 함수
def extract_domain(raw_url):
    # http(s):// 및 www. 제거
    url = re.sub(r"https?://", "", raw_url, flags=re.IGNORECASE)
    url = re.sub(r"^www\.", "", url, flags=re.IGNORECASE)
    # 경로 부분 제거하여 도메인만 추출
    return url.strip().split('/')[0].split(':')[0] # 포트 번호도 제거

# 유틸: IP 조회 함수
def get_ip_from_dig(domain):
    if not domain: # 빈 도메인 입력 방지
        return "INVALID_DOMAIN"
    try:
        # IPv4 주소만 찾도록 수정 (옵션: A 레코드 명시)
        dig_result = subprocess.check_output(
            ["dig", "+short", "A", domain],
            encoding='utf-8',
            timeout=5 # dig 명령 타임아웃 추가
        )
        # 여러 IP가 반환될 수 있으므로 첫 번째 유효한 IP를 사용
        for line in dig_result.strip().split("\n"):
            line = line.strip()
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", line):
                return line
        return "NO_IP_FOUND" # A 레코드가 있지만 IP 형식이 아닌 경우 (예: CNAME만 있는 경우)
    except subprocess.CalledProcessError:
        # 도메인이 존재하지 않거나 dig 실행 실패
        return "DIG_ERROR_OR_NO_DOMAIN"
    except subprocess.TimeoutExpired:
        return "DIG_TIMEOUT"
    except Exception as e:
        print(f"Error during dig for {domain}: {e}")
        return "DIG_UNEXPECTED_ERROR"

all_entries = []

print(f"HTML 파일 검색 시작 경로: {html_dir}")

if not html_dir.exists() or not html_dir.is_dir():
    print(f"오류: HTML 디렉토리 '{html_dir}'를 찾을 수 없거나 디렉토리가 아닙니다.")
    exit()

html_files_found = list(html_dir.rglob("*.html")) # rglob 사용
if not html_files_found:
    print(f"'{html_dir}' 및 하위 디렉토리에서 HTML 파일을 찾을 수 없습니다.")
else:
    print(f"총 {len(html_files_found)}개의 HTML 파일 검색됨.")

for html_file in html_files_found:
    group_name = html_file.parent.name

    if html_file.parent == html_dir:
        group_name = "unknown_group_at_root" # 또는 다른 기본값
        print(f"알림: 최상위 디렉토리 파일 '{html_file.name}'. 그룹명 '{group_name}'으로 설정.")


    print(f"\n--- 파일 처리 중: {html_file} (그룹: {group_name}) ---")
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) < 50: # 임계값 예시
                print(f"파일 내용이 너무 짧아 건너뜁니다: {html_file}")
                continue
            soup = BeautifulSoup(content, "html.parser")
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다 (이미 삭제되었을 수 있음): {html_file}")
        continue
    except Exception as e:
        print(f"파일 읽기 또는 파싱 오류 ({html_file}): {e}")
        continue

    text_content = soup.get_text(separator=" ") # 공백으로 구분하여 단어 분리 용이
    url_pattern = re.compile(
        r'\b(?:https?://|s?ftps?://)?'  # 프로토콜 (선택적)
        r'(?:www\.)?'  # www (선택적)
        r'([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+' # 서브도메인/도메인 이름
        r'([a-zA-Z]{2,24})' # TLD (최상위 도메인)
        r'(?:[/?#]\S*)?\b', # 경로, 쿼리, 프래그먼트 (선택적)
        re.IGNORECASE
    )
    
    extracted_urls_in_file = set() # 파일 내 중복 URL 방지

    for match in url_pattern.finditer(text_content):
        raw_url = match.group(0).strip()

        # 너무 짧거나 명백히 URL이 아닌 경우 필터링 (예: version 1.0.0)
        if "." not in raw_url or len(raw_url) < 7 or raw_url.count('.') < 1:
            continue
        
        # onion 주소는 제외 (필요에 따라)
        if ".onion" in raw_url:
            # print(f"Onion 주소 건너뜀: {raw_url}")
            continue

        domain = extract_domain(raw_url)
        if not domain: # extract_domain이 빈 문자열 반환 시
            continue

        if raw_url in extracted_urls_in_file:
            continue
        extracted_urls_in_file.add(raw_url)

        ip = get_ip_from_dig(domain)
        print(f"[+] URL: {raw_url} (도메인: {domain}) → IP: {ip}")
        all_entries.append((html_file.name, group_name, raw_url, domain, ip))

try:
    with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["html_file", "group", "url", "domain", "ip_address"])
        writer.writerows(all_entries)
    print(f"\n[✓] 총 {len(all_entries)}개 URL 항목을 {output_csv_path}에 저장했습니다.")
except IOError as e:
    print(f"오류: CSV 파일 '{output_csv_path}' 쓰기 중 문제 발생: {e}")
except Exception as e:
    print(f"오류: CSV 파일 저장 중 예기치 않은 문제 발생: {e}")
