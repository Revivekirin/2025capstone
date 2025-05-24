import os
from dotenv import load_dotenv
from pathlib import Path

from extract.merge_csv import merge_and_update_shodan_csv
from extract.extract_url import process_html_files_and_extract_urls
from extract.extract_shodan import enrich_ips_with_shodan_data

load_dotenv()
BASE_NEWS_DIR = os.getenv("BASE_NEWS_DIR") 
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
ONION_JSON_PATH = os.getenv("ONION_JSON_PATH") 
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")

def run():
    if not BASE_NEWS_DIR:
        print("오류: BASE_NEWS_DIR 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return
    if not OUTPUT_DIR:
        print("오류: OUTPUT_DIR 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return
    if not SHODAN_API_KEY:
        print("오류: SHODAN_API_KEY 환경 변수가 .env 파일에 설정되지 않았습니다.")
        # Shodan 정보 보강 없이 계속 진행할지, 여기서 중단할지 결정. 여기서는 중단.
        return
        
    output_dir_path = Path(OUTPUT_DIR) 
    try: 
        output_dir_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"오류: 출력 디렉토리 '{output_dir_path}' 생성 중 문제 발생: {e}")
        return

    print("\n--- 1. URL 추출 및 개별 CSV 생성 단계 ---")
    process_html_files_and_extract_urls(BASE_NEWS_DIR, OUTPUT_DIR)

    print("\n--- 2. csv 파일 병합 ---")
    merge_and_update_shodan_csv(OUTPUT_DIR)

    print("\n--- 3. Shodan 정보 보강 단계 ---")
    shodan_data_csv_file = output_dir_path / "shodan_data.csv" 
    
    if shodan_data_csv_file.exists():
        enrich_success = enrich_ips_with_shodan_data(str(shodan_data_csv_file), SHODAN_API_KEY)
        if enrich_success:
            print("Shodan 정보 보강 작업이 완료되었습니다.")
        else:
            print("Shodan 정보 보강 작업 중 문제가 발생했거나 변경 사항이 없었습니다.")
    else:
        print(f"오류: Shodan 정보 보강 대상 파일 '{shodan_data_csv_file}'을 찾을 수 없습니다.")
        print("CSV 병합 단계가 정상적으로 완료되었는지 확인해주세요.")

    print("\n모든 작업 완료.")


if __name__ == "__main__":
    run()