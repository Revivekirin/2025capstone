import json
import subprocess
import time
from pathlib import Path

def run_crawler():
    json_path = Path("/app/downloads/onion_list.json")

    if not json_path.exists() or json_path.stat().st_size == 0:
        print("❌ onion_list.json 파일이 없거나 비어있습니다.")
        return

    with open(json_path, "r") as f:
        fqdn_list = json.load(f)

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
            "-L",
            "--max-time", "30",
            f"http://{fqdn}",
            "-o", outfile
        ]

        print(f"실행: {' '.join(curl_cmd)}")
        try:
            subprocess.run(curl_cmd, check=True)
            print(f"저장됨: {outfile}")
        except subprocess.CalledProcessError:
            print(f"curl 실패: {fqdn}")

while True:
    print("\ncurl 크롤러 실행")
    run_crawler()
    print("curl 크롤링 완료, 다음 실행까지 대기")

    time.sleep(10 * 60)  # 10분마다
