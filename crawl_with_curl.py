# import json
# import subprocess
# import time
# from pathlib import Path
# import requests

# def wait_for_tor_proxy_ready(max_retries=10, delay_sec=10):
#     for attempt in range(1, max_retries + 1):
#         try:
#             print(f"[Tor Check] ({attempt}/{max_retries})")
#             proxies = {
#                 'http': 'socks5h://127.0.0.1:9050',
#                 'https': 'socks5h://127.0.0.1:9050'
#             }
#             res = requests.get('https://check.torproject.org/', proxies=proxies, timeout=5)
#             if res.status_code == 200 and "Congratulations" in res.text:
#                 print("[✓] Tor Proxy Ready!")
#                 return
#         except Exception:
#             print("[Waiting for Tor Proxy...]")
#         time.sleep(delay_sec)
#     print("[✖] Tor Proxy not ready after retries. Exiting.")
#     exit(1)

# def run_crawler():
#     json_path = Path("/app/downloads/onion_list.json")

#     if not json_path.exists() or json_path.stat().st_size == 0:
#         print("❌ onion_list.json 파일이 없거나 비어있습니다.")
#         return

#     with open(json_path, "r") as f:
#         fqdn_list = json.load(f)

#     for entry in fqdn_list:
#         fqdn = entry.get("fqdn")
#         if not fqdn:
#             continue

#         outfile = f"/app/downloads/{fqdn.replace('.', '_').replace('/', '')}.html"
#         print(f"📥 크롤링 대상: {fqdn}")
#         curl_cmd = [
#             "curl",
#             "--fail",
#             "--socks5-hostname", "127.0.0.1:9050",
#             "--connect-timeout", "10",
#             "--max-time", "30",
#             "-L",
#             f"http://{fqdn}",
#             "-o", outfile
#         ]

#         print(f"👉 실행: {' '.join(curl_cmd)}")
#         try:
#             subprocess.run(curl_cmd, check=True)
#             print(f"✅ 저장됨: {outfile}")
#         except subprocess.CalledProcessError:
#             print(f"❌ curl 실패: {fqdn}")

# if __name__ == "__main__":
#     wait_for_tor_proxy_ready()  
#     while True:
#         print("\ncurl 크롤러 실행")
#         run_crawler()
#         print("curl 크롤링 완료, 다음 실행까지 대기")
#         time.sleep(10 * 60)

import json
import subprocess
import time
from pathlib import Path
import requests

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

    for entry in fqdn_list:
        fqdn = entry.get("fqdn")
        if not fqdn:
            continue

        outfile = f"/app/downloads/{fqdn.replace('.', '_').replace('/', '')}.html"
        print(f"📥 크롤링 대상: {fqdn}")
        curl_cmd = [
            "curl",
            "--fail",
            "--socks5-hostname", "127.0.0.1:9050",
            "--connect-timeout", "10",
            "--max-time", "30",
            "-L",
            f"http://{fqdn}",
            "-o", outfile
        ]

        print(f"👉 실행: {' '.join(curl_cmd)}")
        try:
            subprocess.run(curl_cmd, check=True)
            print(f"✅ 저장됨: {outfile}")
        except subprocess.CalledProcessError:
            print(f"❌ curl 실패: {fqdn}")

if __name__ == "__main__":
    wait_for_tor_proxy_ready()
    print("\ncurl 크롤러 실행 시작")
    run_crawler()
    print("✅ 모든 작업 완료, curl-crawler 종료합니다.")
    exit(0)
