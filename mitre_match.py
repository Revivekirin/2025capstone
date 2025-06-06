import os
import json
from dotenv import load_dotenv

from utils.file_loader import load_articles_from_directory, load_mitre_techniques
from nlp.translator import translate_boannews_with_argos
from nlp.summarize import add_summaries_to_articles
from mitre.matcher import calculate_mire_embedding, match_articles_to_mitre

load_dotenv()
BASE_NEWS_DIR = os.getenv("BASE_NEWS_DIR") 
mitre_xlsx_path = os.getenv("MITRE_XLSX_PATH") 
output_json_path = os.getenv("OUTPUT_JSON_PATH") 

def main_workflow():
    # --- 1. 설정 및 경로 ---
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
   
    # --- 2. 기사 데이터 로드 ---
    original_news_articles = load_articles_from_directory(BASE_NEWS_DIR)
    if not original_news_articles :
        print("No articles found. Exiting.")
        return

    # --- 3. 특정 출처 기사 번역 ---
    translate_boannews_with_argos(BASE_NEWS_DIR, target_source='boannews')
    news_articles = load_articles_from_directory(BASE_NEWS_DIR)

    # --- 4. 요약 저장 ---
    add_summaries_to_articles(news_articles)
    save_articles_to_json(news_articles, output_path="news_data.json")

    # --- 5. MITRE ATT&CK 기술 정보 로드 ---
    mitre_techniques_info = load_mitre_techniques(mitre_xlsx_path)
    if not mitre_techniques_info:
        print("No MITRE techniques found. Exiting.")
    else:
        mitre_embeddings_array, valid_mitre_techniques = calculate_mire_embedding(mitre_techniques_info)
        if mitre_embeddings_array is None:
            print("No valid MIRE embeddings found. Exiting.")
        else:
            # --- 6. 기사와 MITRE 기술 매칭 ---
            final_articles_with_mitre = match_articles_to_mitre(news_articles, mitre_embeddings_array, valid_mitre_techniques)
    
    # --- 7. 결과 저장 ---
    existing_data = []
    if os.path.exists(output_json_path):
        with open(output_json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

    # 새 데이터 병합
    merged_data = existing_data + (final_articles_with_mitre if 'final_articles_with_mitre' in locals() else news_articles)

    # 병합 결과 저장
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=4)
    # print(f"Saving results to {output_json_path}...")
    # try:
    #     with open(output_json_path, 'w', encoding='utf-8') as json_file:
    #         json.dump(final_articles_with_mitre if 'final_articles_with_mitre' in locals() else processed_news_list, json_file, ensure_ascii=False, indent=4, default=str)
    #     print(f"Results saved to {output_json_path}.")
    # except Exception as e:
    #     print(f"Error saving results: {e}")

def save_articles_to_json(news_articles, output_path=f"{output_json_path}"):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(news_articles, f, ensure_ascii=False, indent=4)
        print(f"저장 완료: {output_path}")
    except Exception as e:
        print(f"저장 중 오류 발생: {e}")


if __name__ == "__main__": main_workflow() 