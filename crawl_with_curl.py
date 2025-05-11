import json
import subprocess
import time
from pathlib import Path
import requests
from datetime import datetime, timedelta

def wait_for_tor_proxy_ready(max_retries=10, delay_sec=10):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Tor Check] ({attempt}/{max_retries})")
            proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
            res = requests.get('https://check.torproject.org/', proxies=proxies, timeout=5)
            if res.status_code == 200 and "Congratulations" in res.text:
                print("[✓] Tor Proxy Ready!")
                return
        except Exception:
            print("[Waiting for Tor Proxy...]")
        time.sleep(delay_sec)
    print("[✖] Tor Proxy not ready after retries. Exiting.")
    exit(1)

def run_crawler():
    json_path = Path("/app/downloads/onion_list.json")

    if not json_path.exists() or json_path.stat().st_size == 0:
        print("❌ onion_list.json 파일이 없거나 비어있습니다. 종료합니다.")
        return

    with open(json_path, "r") as f:
        fqdn_list = json.load(f)

    if not fqdn_list:
        print("❌ FQDN 리스트가 비어있습니다. 종료합니다.")
        return

    today_str = datetime.now().strftime("%Y%m%d")
    # today_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    # 여기에 특수한 URL 패턴을 가지는 그룹들을 추가
    special_groups = ["play", "blacksuit", "kairos"]

    for entry in fqdn_list:
        fqdn = entry.get("fqdn")
        group = entry.get("group", "").lower().strip()  # group 필드가 없거나 대소문자 대비

        if not fqdn:
            continue

        print(f"\n크롤링 시작: {fqdn} (group: {group})")

        for page_num in range(1, 6):
            if group in special_groups:
                if group == "kairos":
                    if page_num == 1:
                        url = f"http://{fqdn}/"
                        suffix = "page1"
                    else:
                        url = f"http://{fqdn}/?PAGEN_1={page_num}"
                        suffix = f"page{page_num}"
                else:
                    if page_num == 1:
                        url = f"http://{fqdn}/"
                        suffix = "page1"
                    else:
                        url = f"http://{fqdn}/index.php?page={page_num}"
                        suffix = f"page{page_num}"
            else:
                if page_num == 1:
                    url = f"http://{fqdn}/"
                    suffix = "page1"
                else:
                    url = f"http://{fqdn}/?page={page_num}"
                    suffix = f"page{page_num}"


            filename = f"{group}_{today_str}_{suffix}.html"
            outfile = f"/app/downloads/{filename}"

            print(f"👉 요청: {url}")
            curl_cmd = [
                "curl",
                "--fail",
                "--socks5-hostname", "127.0.0.1:9050",
                "--connect-timeout", "10",
                "--max-time", "30",
                "-L",
                url,
                "-o", outfile
            ]

            try:
                subprocess.run(curl_cmd, check=True)
                print(f"✅ 저장됨: {outfile}")
            except subprocess.CalledProcessError:
                print(f"❌ 페이지 없음 또는 실패: {url} → 다음 fqdn으로 이동")
                break  # 다음 fqdn으로

def main():
    wait_for_tor_proxy_ready()
    print("\ncurl 크롤러 실행 시작")
    run_crawler()
    print("모든 작업 완료, curl-crawler 종료합니다.")

if __name__ == "__main__":
    main()
