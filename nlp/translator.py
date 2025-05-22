from transformers import MarianMTModel, MarianTokenizer
import torch
import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

MODEL_NAME_KO_EN = 'Helsinki-NLP/opus-mt-ko-en'
print(f"Loading model {MODEL_NAME_KO_EN}...")
try:
    TRANSLATION_TOKENIZER = MarianTokenizer.from_pretrained(MODEL_NAME_KO_EN, token=HF_TOKEN if HF_TOKEN else None)
    TRANSLATION_MODEL = MarianMTModel.from_pretrained(MODEL_NAME_KO_EN, token=HF_TOKEN if HF_TOKEN else None)
    TRANSLATION_MODEL.eval()
    print("Translation Model loaded successfully.")
except Exception as e:
    print(f"Error loading translation model: {e}")
    TRANSLATION_MODEL = None
    TRANSLATION_TOKENIZER = None

def translate_korean_to_english(text, max_chunk_tokens=512, stride_tokens=300):
    if not TRANSLATION_TOKENIZER or not TRANSLATION_MODEL:
        print("Translation model is not loaded. Returning original text.")
        return text
    if not text or not text.strip():
        return ""


    inputs = TRANSLATION_TOKENIZER(text, return_tensors="pt", truncation=False)
    input_ids = inputs.input_ids[0]

    translated_chunks = []

    currnet_pos = 0
    while currnet_pos < len(input_ids):
        end_pos = min(currnet_pos+max_chunk_tokens, len(input_ids))
        chunk_ids = input_ids[currnet_pos:end_pos]

        chunk_pt = torch.tensor([chunk_ids.tolist()])

        with torch.no_grad():
            translated_ids = TRANSLATION_MODEL.generate(chunk_pt, max_length=2*max_chunk_tokens)
            translated_text_chunk = TRANSLATION_TOKENIZER.decode(translated_ids[0], skip_special_tokens=True)
            translated_chunks.append(translated_text_chunk)

        if end_pose == len(input_ids):
            break
        currnet_pos += stride_tokens
    
    return " ".join(translated_chunks)
    
def process_articles_for_translation(news_list, target_source='boannews'):
    translated_news_list = []
    other_news_list = []

    print(f"Translating articles from {target_source}...")
    for i, article in enumerate(news_list):
        if article['source'] == target_source:
            print(f"Translating article {i+1}/{len(news_list)}: {article['title']}")
            try:
                translated_title = translate_korean_to_english(article['title'])
                translated_content = translate_korean_to_english(article['content'])
                translated_news_list.append({
                    'title': translated_title,
                    'content': translated_content,
                    'source': article['source'],
                })
                print(f"Translated: {article['title']}")
            except Exception as e:
                print(f"Error translating article {i+1}: {e}")
        else:
            other_news_list.append(article)
    print(f"Translated completed. {len(translated_news_list)} articles translated.")
    return other_news_list + translated_news_list