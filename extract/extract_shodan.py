import os
import pandas as pd
import subprocess
import json
import time
from dotenv import load_dotenv

def extract_shodan_features_from_api_response(data): # data here is the merged_data
    def get_nested(d, *keys):
        # This get_nested is from your original.
        # It returns None if the final resolved value is an empty dict.
        for key in keys:
            d = d.get(key, {}) 
        return d if d else None

    # Using original defaults and structure
    features = {
            "product": data.get("product", []), 
            "version": data.get("version", []), 
            "cpe": data.get("cpe", []),     
            "cpe23": data.get("cpe23", []),     
            # This line correctly handles get_nested possibly returning None (from empty dicts)
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
            "country_code": data.get("country_code") or data.get("location", {}).get("country_code"),
            "region_code": data.get("region_code") or data.get("location", {}).get("region_code"),
            "ssl_issuer": get_nested(data, "ssl", "cert", "issuer"),
            "ssl_subject": get_nested(data, "ssl", "cert", "subject")
        }

    for k, v in features.items():
        if isinstance(v, list):
            features[k] = ", ".join(map(str, v))
        elif isinstance(v, dict):
            features[k] = json.dumps(v)
    
    #print(features) # Print statement back in its original position
    return features

def enrich_ips_with_shodan_data(csv_filepath: str, api_key: str):
    """
    주어진 CSV 파일에서 'ip_address'를 읽어 Shodan API로 정보를 조회하고,
    추출된 feature들로 CSV 파일을 업데이트합니다.
    'product' 컬럼이 비어있는 행만 대상으로 조회합니다.

    Args:
        csv_filepath (str): Shodan 데이터를 추가/업데이트할 CSV 파일 경로.
        api_key (str): Shodan API 키.
    """
    if not api_key:
        print("오류: Shodan API 키가 제공되지 않았습니다.")
        return False
    
    if not os.path.exists(csv_filepath):
        print(f"오류: CSV 파일을 찾을 수 없습니다 - {csv_filepath}")
        return False

    try:
        df = pd.read_csv(csv_filepath)
    except Exception as e:
        print(f"오류: CSV 파일 '{csv_filepath}' 로드 중 문제 발생: {e}")
        return False

    if 'ip_address' not in df.columns:
        print(f"오류: CSV 파일에 'ip_address' 컬럼이 없습니다.")
        return False

    shodan_feature_columns = [
        "product", "version", "cpe", "cpe23", "components", "ssh_key", 
        "ssh_kex", "ssh_mac", "ssh_cipher", "ssl_ja3s", "ssl_jarm", 
        "ssl_fingerprint", "hostnames", "domains", "vulns", "tags", 
        "server", "asn", "org", "isp", "country_code", "region_code", 
        "ssl_issuer", "ssl_subject"
    ]
    
    made_changes = False
    for col in shodan_feature_columns:
        if col not in df.columns:
            df[col] = pd.NA 
            made_changes = True 

    print(f"'{csv_filepath}' 파일에서 Shodan 정보 보강 시작...")
    enriched_count = 0
    processed_ips_in_batch = 0 

    for index, row in df.iterrows():
        shodan_ip = row['ip_address']
        
        if pd.isna(shodan_ip) or shodan_ip == "NO_IP_FOUND":
            continue

        shodan_check_columns = ["asn", "product", "vulns", "ssl_fingerprint"]
        is_all_empty = all(
            pd.isna(row.get(col)) or str(row.get(col)).strip() == "" or str(row.get(col)).lower() == 'nan'
            for col in shodan_check_columns
        )
        if not is_all_empty:
            continue  

        try:
            shodan_ip_str = str(shodan_ip)
            cmd = f'curl -s "https://api.shodan.io/shodan/host/{shodan_ip_str}?key={api_key}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"Error running curl for {shodan_ip_str}: {result.stderr}")
                time.sleep(1) 
                continue

            if not result.stdout:
                print(f"No data returned from Shodan for {shodan_ip_str}.")
                time.sleep(1)
                continue
            
            api_response_data = json.loads(result.stdout) # This is the raw full response from Shodan

            if api_response_data.get("error"):
                print(f"Shodan API error for {shodan_ip_str}: {api_response_data['error']}")
                if "request limit reached" in api_response_data['error'].lower():
                    print("Shodan API request limit reached. Stopping for now.")
                    if made_changes or enriched_count > 0:
                        try:
                            df.to_csv(csv_filepath, index=False)
                            print(f"진행 상황 저장됨: {csv_filepath} ({enriched_count}개 IP 정보 추가/업데이트됨)")
                        except Exception as e_save:
                            print(f"CSV 파일 저장 중 오류 발생 '{csv_filepath}': {e_save}")
                    return False 
                time.sleep(5) 
                continue

            # ** CRUCIAL: Create merged_data as per original implied logic **
            # This dictionary will be passed to extract_shodan_features_from_api_response
            merged_data = {}
            for item in api_response_data.get("data", []):
                merged_data.update(item)
            merged_data.update({k: v for k, v in api_response_data.items() if k != "data"})
            
            features = extract_shodan_features_from_api_response(merged_data)

            for col_name, value in features.items():
                if col_name in df.columns:
                    df.loc[index, col_name] = value
            
            made_changes = True
            enriched_count += 1
            processed_ips_in_batch +=1
            print(f"{shodan_ip_str} 처리 완료. 현재까지 {enriched_count}개 IP 보강됨.")

            time.sleep(1.1) 

        except json.JSONDecodeError:
            print(f"{shodan_ip_str} 처리 실패: Shodan 응답이 유효한 JSON이 아닙니다. 응답: {result.stdout[:200]}...")
            time.sleep(1)
        except subprocess.TimeoutExpired:
            print(f"{shodan_ip_str} 처리 실패: Shodan API 요청 시간 초과.")
            time.sleep(1)
        except Exception as e:
            print(f"{shodan_ip_str} 처리 중 예상치 못한 오류 발생: {e}")
            time.sleep(1)

    if made_changes or processed_ips_in_batch > 0 : 
        try:
            df.to_csv(csv_filepath, index=False)
            print(f"성공: CSV 파일이 업데이트되었습니다 - {csv_filepath}")
            print(f"이번 실행에서 총 {processed_ips_in_batch}개의 IP 정보가 추가/업데이트되었습니다.")
        except Exception as e:
            print(f"오류: CSV 파일 저장 중 문제 발생 '{csv_filepath}': {e}")
            return False
    else:
        print("CSV 파일에 변경 사항이 없습니다. 저장하지 않습니다.")

    return True


if __name__ == '__main__':
    load_dotenv()
    SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR")
    enrich_ips_with_shodan_data(OUTPUT_DIR, SHODAN_API_KEY)