import json
import subprocess
import time
from pathlib import Path
import requests
from datetime import datetime, timedelta
import logging
import re 
from glob import glob

# --- 설정 값 ---
BASE_DOWNLOAD_DIR = Path("/app/downloads") # 기본 다운로드 디렉토리
ONION_LIST_PATH = BASE_DOWNLOAD_DIR / "onion_list.json"
TOR_PROXY_ADDRESS = "127.0.0.1:9050"
MAX_PAGES_PER_FQDN = 5
CURL_CONNECT_TIMEOUT = 10  # curl 연결 타임아웃
CURL_MAX_TIME = 30         # curl 전체 최대 실행 시간
SUBPROCESS_TIMEOUT = CURL_MAX_TIME + 10 # subprocess의 타임아웃 (curl max_time 보다 길게)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0" # 예시 User-Agent

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clean_old_group_files(group, today_str):
    """해당 그룹 폴더에서 오늘 날짜가 아닌 HTML 파일 삭제"""
    group_dir = BASE_DOWNLOAD_DIR / group
    if not group_dir.exists():
        return
    
    logger.info(f"[정리] '{group}' 그룹 디렉토리 내 오래된 파일 삭제 중...")
    for file_path in group_dir.glob(f"{group}_*.html"):
        if today_str not in file_path.name:
            try:
                file_path.unlink()
                logger.info(f"🗑️ 삭제됨: {file_path}")
            except Exception as e:
                logger.warning(f"삭제 실패: {file_path} | 이유: {e}")


def sanitize_filename(filename_component):
    """파일명으로 사용하기 안전한 문자열로 변환"""
    return re.sub(r'[^\w\-_\.]', '_', str(filename_component))


def get_normalized_group_name(entry):
    """entry에서 group을 안전하게 정규화하여 반환"""
    raw_group = entry.get("group", "").strip().lower()
    return sanitize_filename(raw_group if raw_group else "unknown_group")


def wait_for_tor_proxy_ready(max_retries=10, delay_sec=10):
    logger.info("Tor 프록시 준비 상태 확인 시작...")
    for attempt in range(1, max_retries + 1):
        logger.info(f"[Tor Check] ({attempt}/{max_retries})")
        try:
            proxies = {
                'http': f'socks5h://{TOR_PROXY_ADDRESS}',
                'https': f'socks5h://{TOR_PROXY_ADDRESS}'
            }
            res = requests.get('https://check.torproject.org/', proxies=proxies, timeout=5)
            if res.status_code == 200 and "Congratulations" in res.text:
                logger.info("[✓] Tor Proxy Ready!")
                return True
        except Exception as e:
            logger.warning(f"[Waiting for Tor Proxy...] 오류: {e}")
        time.sleep(delay_sec)
    logger.error("[✖] Tor Proxy not ready after retries. Exiting.")
    return False

def fetch_url_with_curl(url, output_filepath):
    """주어진 URL을 curl을 사용해 파일로 저장합니다."""
    logger.info(f"👉 요청: {url}")
    curl_cmd = [
        "curl",
        "--fail", # HTTP 오류 시 0이 아닌 종료 코드 반환
        "--socks5-hostname", TOR_PROXY_ADDRESS,
        "-A", USER_AGENT, # User-Agent 추가
        "--connect-timeout", str(CURL_CONNECT_TIMEOUT),
        "--max-time", str(CURL_MAX_TIME),
        "-L", # 리다이렉션 따르기
        url,
        "-o", str(output_filepath) # Path 객체를 문자열로 변환
    ]

    try:
        # 출력 디렉토리 생성 (없으면)
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
        
        process = subprocess.run(curl_cmd, check=True, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
        logger.info(f"저장됨: {output_filepath}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"페이지 없음 또는 curl 실패 (종료 코드 {e.returncode}): {url}")
        logger.debug(f"Curl stdout: {e.stdout}")
        logger.debug(f"Curl stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"Curl 실행 시간 초과: {url}")
        return False
    except Exception as e:
        logger.error(f"알 수 없는 오류 발생 ({url}): {e}")
        return False



def run_crawler():
    if not ONION_LIST_PATH.exists() or ONION_LIST_PATH.stat().st_size == 0:
        logger.error(f"{ONION_LIST_PATH} 파일이 없거나 비어있습니다. 종료합니다.")
        return

    try:
        with open(ONION_LIST_PATH, "r") as f:
            fqdn_list = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"{ONION_LIST_PATH} 파일의 JSON 형식이 잘못되었습니다. 종료합니다.")
        return
    except Exception as e:
        logger.error(f"{ONION_LIST_PATH} 파일 로드 중 오류 발생: {e}. 종료합니다.")
        return


    if not fqdn_list:
        logger.error("FQDN 리스트가 비어있습니다. 종료합니다.")
        return

    today_str = datetime.now().strftime("%Y%m%d")
    # today_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d") # 어제 날짜 테스트용

    special_groups = ["play", "blacksuit", "kairos"] # 페이지네이션 방식이 다른 그룹

    total_fqdns = len(fqdn_list)

    all_groups = set(get_normalized_group_name(entry) for entry in fqdn_list)
    for group in all_groups:
        clean_old_group_files(group, today_str)

    for i, entry in enumerate(fqdn_list):
        fqdn = entry.get("fqdn")
        group = get_normalized_group_name(entry)

        if not fqdn:
            logger.warning(f"FQDN 정보가 없는 항목 건너뜀: {entry}")
            continue

        logger.info(f"\n--- [{i+1}/{total_fqdns}] 크롤링 시작: {fqdn} (group: {group}) ---")

        for page_num in range(1, MAX_PAGES_PER_FQDN + 1):
            # URL 및 파일명 suffix 생성 로직
            if group in special_groups:
                if group == "kairos":
                    url = f"http://{fqdn}/" if page_num == 1 else f"http://{fqdn}/?PAGEN_1={page_num}"
                else: # play, blacksuit 등
                    url = f"http://{fqdn}/" if page_num == 1 else f"http://{fqdn}/index.php?page={page_num}"
            else: # 일반 그룹
                url = f"http://{fqdn}/" if page_num == 1 else f"http://{fqdn}/?page={page_num}"
            
            suffix = f"page{page_num}"
            filename = f"{group}_{today_str}_{suffix}.html"
            # 출력 파일 경로를 BASE_DOWNLOAD_DIR 기준으로 설정
            outfile_path = BASE_DOWNLOAD_DIR / group / filename # 그룹별 하위 디렉토리 생성
            # outfile_path = BASE_DOWNLOAD_DIR / filename # 모든 파일을 동일 디렉토리에 저장하고 싶다면

            if not fetch_url_with_curl(url, outfile_path):
                logger.warning(f"페이지 {page_num} 가져오기 실패. 다음 FQDN으로 이동: {fqdn}")
                break # 현재 FQDN의 다음 페이지 크롤링 중단, 다음 FQDN으로 넘어감

def main():
    if not wait_for_tor_proxy_ready():
        return # Tor 프록시 준비 안되면 종료

    logger.info("\n=== curl 크롤러 실행 시작 ===")
    run_crawler()
    logger.info("=== 모든 작업 완료, curl-crawler 종료합니다. ===")

if __name__ == "__main__":
    main()
