from transformers import MarianMTModel, MarianTokenizer
import torch
import os
from dotenv import load_dotenv
import argostranslate.package
import argostranslate.translate

# def translate_boannews_with_argos(news_list, base_dir, target_source="boannews"):
#     from_code = "ko"
#     to_code = "en"

#     installed_languages = argostranslate.translate.get_installed_languages()
#     from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
#     to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)

#     if not from_lang or not to_lang:
#         print(f"언어 쌍 '{from_code}' → '{to_code}'를 찾을 수 없습니다. 먼저 모델을 설치하세요.")
#         return news_list

#     translator = from_lang.get_translation(to_lang)

#     translated_news_list = []
#     other_news_list = []

#     print(f"Translating and saving boannews articles...")

#     for i, article in enumerate(news_list):
#         if article.get('source') != target_source:
#             other_news_list.append(article)
#             continue

#         title_to_translate = article.get('title', '')
#         content_to_translate = article.get('content', '')

#         if not title_to_translate.strip() and not content_to_translate.strip():
#             print(f"  Skipping empty article {i+1}/{len(news_list)}")
#             other_news_list.append(article)
#             continue

#         try:
#             translated_title = translator.translate(title_to_translate) if title_to_translate else ''
#             translated_content = translator.translate(content_to_translate) if content_to_translate else ''

#             # 파일 경로 추정
#             rel_path = os.path.join(article['source'], translated_title[:20].replace(" ", "_").replace("/", "_"))
#             target_folder = os.path.join(base_dir, rel_path)
#             article_path = os.path.join(target_folder, "article.txt")

#             os.makedirs(target_folder, exist_ok=True)

#             with open(article_path, "w", encoding="utf-8") as f:
#                 f.write(f"제목: {translated_title}\n\n")
#                 f.write("URL: \n\n")
#                 f.write(translated_content.strip())

#             translated_article = article.copy()
#             translated_article.update({
#                 'title': translated_title,
#                 'content': translated_content,
#                 'translated': True,
#                 'path': article_path
#             })

#             translated_news_list.append(translated_article)
#             print(f"  [✔] Translated & saved: {article_path}")

#         except Exception as e:
#             print(f"  [!] Failed to translate article {i+1}/{len(news_list)}: {e}")
#             other_news_list.append(article)

#     print(f"\nTranslation process completed. {len(translated_news_list)} articles translated and saved.")
#     return other_news_list + translated_news_list

import os
import glob
from argostranslate import translate

def translate_boannews_with_argos(base_dir, target_source="boannews"):
    from_code = "ko"
    to_code = "en"

    installed_languages = translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)

    if not from_lang or not to_lang:
        print(f"언어 쌍 '{from_code}' → '{to_code}'를 찾을 수 없습니다. 먼저 모델을 설치하세요.")
        return []

    translator = from_lang.get_translation(to_lang)

    translated_articles = []

    print(f"Translating articles under: {base_dir}/{target_source}/")

    base_target_path = os.path.join(base_dir, target_source)
    article_paths = glob.glob(os.path.join(base_target_path, "*", "*", "article.txt"))

    for article_path in article_paths:
        try:
            with open(article_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                continue

            translated_content = translator.translate(content)

            # 덮어쓰기
            with open(article_path, "w", encoding="utf-8") as f:
                f.write(translated_content)

            # 메타데이터 기록
            rel_path = os.path.relpath(article_path, base_dir)
            translated_articles.append({
                "source": target_source,
                "path": article_path,
                "rel_path": rel_path,
                "content": translated_content,
                "translated": True
            })

            print(f"[✔] Translated & overwritten: {rel_path}")

        except Exception as e:
            print(f"[!] Failed to translate {article_path}: {e}")

    print(f"\nTranslation completed. Total: {len(translated_articles)} articles.")
    return translated_articles



# 번역 언어 모델 사용
# load_dotenv()
# HF_TOKEN = os.getenv("HF_TOKEN")

# MODEL_NAME_KO_EN = 'Helsinki-NLP/opus-mt-ko-en'
# print(f"Loading translation model: {MODEL_NAME_KO_EN}") 
# try:
#     TRANSLATION_TOKENIZER = MarianTokenizer.from_pretrained(MODEL_NAME_KO_EN, token=HF_TOKEN if HF_TOKEN else None)
#     TRANSLATION_MODEL = MarianMTModel.from_pretrained(MODEL_NAME_KO_EN, token=HF_TOKEN if HF_TOKEN else None)
#     TRANSLATION_MODEL.eval()
#     print("Translation Model loaded successfully.")
# except Exception as e:
#     print(f"Error loading translation model: {e}")
#     TRANSLATION_MODEL = None
#     TRANSLATION_TOKENIZER = None

# def translate_korean_to_english(text, max_chunk_tokens=512, stride_tokens=400): 
#     if not TRANSLATION_TOKENIZER or not TRANSLATION_MODEL:
#         print("Translation model is not loaded. Returning original text.")
#         return text
#     if not text or not text.strip(): # 비어있거나 공백만 있는 텍스트 처리
#         return ""
#     inputs = TRANSLATION_TOKENIZER(text, return_tensors="pt", truncation=False)
#     input_ids = inputs.input_ids[0] 

#     if len(input_ids) == 0: # 토큰화 결과가 비어있는 경우
#         return ""

#     translated_chunks = []
#     current_pos = 0

#     while current_pos < len(input_ids):
#         end_pos = min(current_pos + max_chunk_tokens, len(input_ids))
#         chunk_ids = input_ids[current_pos:end_pos]

#         if len(chunk_ids) == 0:
#             break

#         chunk_pt = chunk_ids.unsqueeze(0) 

#         try:
#             with torch.no_grad():
#                 output_max_length = min(len(chunk_ids) * 2 + 50, TRANSLATION_MODEL.config.max_length)


#                 translated_ids = TRANSLATION_MODEL.generate(
#                     chunk_pt,
#                     max_length=output_max_length,
#                     num_beams=4, # 선택적: 품질 향상, 속도 저하
#                     early_stopping=True # 선택적: num_beams 사용 시
#                 )
#             # 디코딩
#             translated_text_chunk = TRANSLATION_TOKENIZER.decode(translated_ids[0], skip_special_tokens=True)
#             translated_chunks.append(translated_text_chunk)
#         except Exception as e:
#             print(f"  Error during model.generate() or decode() for a chunk: {e}")
#             print(f"  Problematic chunk (IDs): {chunk_ids.tolist()}") # 문제 청크 ID 출력


#         if end_pos == len(input_ids): # 모든 토큰을 처리했으면 루프 종료
#             break
#         current_pos += stride_tokens

#         if current_pos >= end_pos and end_pos < len(input_ids):
#             current_pos = end_pos

#     return " ".join(translated_chunks)


# def process_articles_for_translation(news_list, target_source='boannews'):
#     translated_news_list = []
#     other_news_list = [] # 번역되지 않거나 실패한 기사를 담을 리스트

#     print(f"Translating articles from source: {target_source}") # 오타 수정: from {target_source}...
#     for i, article in enumerate(news_list):
#         if article['source'] == target_source:
#             title_to_translate = article.get('title', '')
#             content_to_translate = article.get('content', '')

#             # 제목과 내용이 모두 비어있는 경우 건너뛰기
#             if not title_to_translate.strip() and not content_to_translate.strip():
#                 print(f"  Skipping empty article {i+1}/{len(news_list)} (no title and content)")
#                 other_news_list.append(article) # 빈 기사도 원본 유지
#                 continue
            
#             print(f"Translating article {i+1}/{len(news_list)}: {title_to_translate[:50]}...") # 제목 일부만 출력
#             try:
#                 # 각 필드가 비어있지 않을 때만 번역 시도
#                 translated_title = translate_korean_to_english(title_to_translate) if title_to_translate.strip() else ""
#                 translated_content = translate_korean_to_english(content_to_translate) if content_to_translate.strip() else ""
                
#                 translated_news_list.append({
#                     'title': translated_title,
#                     'content': translated_content,
#                     'source': article['source'],
#                 })
#                 print(f"Translated: {title_to_translate[:50]}...")
#             except Exception as e:
#                 print(f"Error translating article {i+1} ('{title_to_translate[:50]}...'): {e}")
#                 other_news_list.append(article)
#         else:
#             other_news_list.append(article) 
            
#     print(f"Translation process completed. {len(translated_news_list)} articles translated.")
#     return other_news_list + translated_news_list

