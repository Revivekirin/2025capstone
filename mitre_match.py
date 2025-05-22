import os
import json
from dotenv import load_dotenv

from utils.file_loader import load_articles_from_directory, load_mitre_techniques
from nlp.translator import process_articles_for_translation
from mitre.matcher import calculate_mire_embedding, match_articles_to_mitre

load_dotenv()
BASE_NEWS_DIR = os.getenv("BASE_NEWS_DIR") 
mitre_xlsx_path = os.getenv("MITRE_XLSX_PATH") 
output_json_path = os.getenv("OUTPUT_JSON_PATH") 

def main_workflow():
    # --- 1. 설정 및 경로 ---
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
   
    # --- 2. 기사 데이터 로드 ---
    news_articles = load_articles_from_directory(BASE_NEWS_DIR)
    if not news_articles:
        print("No articles found. Exiting.")
        return

    # --- 3. 특정 출처 기사 번역 ---
    processed_news_list = process_articles_for_translation(news_articles, target_source='boannews')

    # --- 4. MITRE ATT&CK 기술 정보 로드 ---
    mitre_techniques_info = load_mitre_techniques(mitre_xlsx_path)
    if not mitre_techniques_info:
        print("No MITRE techniques found. Exiting.")
    else:
        mitre_embeddings_array, valid_mitre_techniques = calculate_mire_embedding(mitre_techniques_info)
        if mitre_embeddings_array is None:
            print("No valid MIRE embeddings found. Exiting.")
        else:
            # --- 5. 기사와 MITRE 기술 매칭 ---
            final_articles_with_mitre = match_articles_to_mitre(processed_news_list, mitre_embeddings_array, valid_mitre_techniques)
    
    # --- 6. 결과 저장 ---
    print(f"Saving results to {output_json_path}...")
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(final_articles_with_mitre if 'final_articles_with_mitre' in locals() else processed_news_list, json_file, ensure_ascii=False, indent=4, default=str)
        print(f"Results saved to {output_json_path}.")
    except Exception as e:
        print(f"Error saving results: {e}")


if __name__ == "__main__": main_workflow() 