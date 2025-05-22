# nlp/embedder.py
from transformers import AutoTokenizer, AutoModel
import torch
import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

MODEL_NAME_DARKBERT = "s2w-ai/DarkBERT" # 또는 사용하는 임베딩 모델 이름
print(f"Loading embedding model: {MODEL_NAME_DARKBERT}")
try:
    # --- 여기가 수정된 부분 ---
    EMBEDDING_TOKENIZER = AutoTokenizer.from_pretrained(
        MODEL_NAME_DARKBERT,
        token=HF_TOKEN if HF_TOKEN else None,
        add_prefix_space=True  # 이 옵션을 추가합니다.
    )
    # -----------------------
    EMBEDDING_MODEL = AutoModel.from_pretrained(MODEL_NAME_DARKBERT, token=HF_TOKEN if HF_TOKEN else None)
    EMBEDDING_MODEL.eval()
    print("Embedding model loaded successfully.")
except Exception as e:
    print(f"Error loading embedding model: {e}")
    EMBEDDING_TOKENIZER = None
    EMBEDDING_MODEL = None

# get_segmented_embedding 함수는 이전 답변의 수정된 버전 그대로 사용
def get_segmented_embedding(text, max_tokens=512, stride=256):
    if not EMBEDDING_TOKENIZER or not EMBEDDING_MODEL:
        print("Embedding model not available.")
        return None

    if not text or not text.strip():
        print("Warning: Empty text provided for embedding. Returning None.")
        return None

    all_tokens = EMBEDDING_TOKENIZER.tokenize(text, add_special_tokens=False)

    if not all_tokens:
        print("Warning: Text resulted in no tokens. Returning None.")
        return None

    embeddings = []

    for i in range(0, len(all_tokens), stride):
        chunk_tokens_list = all_tokens[i : i + max_tokens - 2] # for [CLS] and [SEP]

        inputs = EMBEDDING_TOKENIZER(
            chunk_tokens_list,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            max_length=max_tokens,
            padding="max_length"
        )

        with torch.no_grad():
            outputs = EMBEDDING_MODEL(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :]
        embeddings.append(cls_embedding)

    if not embeddings:
        print("Warning: No embeddings generated for the text. Returning None.")
        return None
    
    squeezed_embeddings = [emb.squeeze(0) for emb in embeddings]
    if not squeezed_embeddings:
        return None
        
    stacked_embeddings = torch.stack(squeezed_embeddings, dim=0)
    mean_embedding = torch.mean(stacked_embeddings, dim=0)
    
    return mean_embedding.cpu().numpy()
# from transformers import AutoTokenizer, AutoModel
# import torch
# import os
# from dotenv import load_dotenv

# load_dotenv()
# HF_TOKEN = os.getenv("HF_TOKEN")

# MODEL_NAME_DARKBERT = "s2w-ai/DarkBERT"
# print(f"Loading model {MODEL_NAME_DARKBERT}...")
# try:
#     EMBEDDING_TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME_DARKBERT, token=HF_TOKEN if HF_TOKEN else None)
#     EMBEDDING_MODEL = AutoModel.from_pretrained(MODEL_NAME_DARKBERT, token=HF_TOKEN if HF_TOKEN else None)
#     EMBEDDING_MODEL.eval()
#     print("DarkBERT Model loaded successfully.")
# except Exception as e:
#     print(f"Error loading DarkBERT model: {e}")
#     EMBEDDING_TOKENIZER = None
#     EMBEDDING_MODEL = None


# def get_segmented_embedding(text, max_tokens=512, stride=256):
#     if not EMBEDDING_TOKENIZER or not EMBEDDING_MODEL:
#         print("Embedding model is not loaded. Returning None.")
#         return None

#     if not text or not text.strip():
#         return None

#     tokens = EMBEDDING_TOKENIZER(text)

#     if not tokens:
#         print("Warining: No tokens found for the input text.")
#         return None

#     embeddings = []

#     for i in range(0, len(tokens), stride):
#         chunk_tokens = tokens[i:i + max_tokens]
#         chunk_text = EMBEDDING_TOKENIZER.convert_tokens_to_string(chunk_tokens)
#         inputs = EMBEDDING_TOKENIZER(chunk_text, return_tensors="pt", truncation=True, max_length=max_tokens, padding=True)

#         with torch.no_grad():
#             outputs = EMEDDING_MODEL(**inputs)

#         cls_embedding = outputs.last_hidden_state[:, 0, :]
#         embeddings.append(cls_embedding)

#     if not embeddings:
#         print("Warning: No embeddings found for the input text.")
#         return None
#     mean_embedding = torch.mean(torch.cat(embeddings, dim=0), dim=0)
#     return mean_embedding.squeeze().numpy()