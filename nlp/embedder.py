from transformers import AutoTokenizer, AutoModel
import torch
import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

MODEL_NAME_DARKBERT = "s2w-ai/DarkBERT"
print(f"Loading model {MODEL_NAME_DARKBERT}...")
try:
    EMBEDDING_TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME_DARKBERT, token=HF_TOKEN if HF_TOKEN else None)
    EMBEDDING_MODEL = AutoModel.from_pretrained(MODEL_NAME_DARKBERT, token=HF_TOKEN if HF_TOKEN else None)
    EMBEDDING_MODEL.eval()
    print("DarkBERT Model loaded successfully.")
except Exception as e:
    print(f"Error loading DarkBERT model: {e}")
    EMBEDDING_TOKENIZER = None
    EMBEDDING_MODEL = None


def get_segmented_embedding(text, max_tokens=512, stride=256):
    if not EMBEDDING_TOKENIZER or not EMBEDDING_MODEL:
        print("Embedding model is not loaded. Returning None.")
        return None

    if not text or not text.strip():
        return None

    tokens = EMBEDDING_TOKENIZER(text)

    if not tokens:
        print("Warining: No tokens found for the input text.")
        return None

    embeddings = []

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = EMBEDDING_TOKENIZER.convert_tokens_to_string(chunk_tokens)
        inputs = EMBEDDING_TOKENIZER(chunk_text, return_tensors="pt", truncation=True, max_length=max_tokens, padding=True)

        with torch.no_grad():
            outputs = EMEDDING_MODEL(**inputs)

        cls_embedding = outputs.last_hidden_state[:, 0, :]
        embeddings.append(cls_embedding)

    if not embeddings:
        print("Warning: No embeddings found for the input text.")
        return None
    mean_embedding = torch.mean(torch.cat(embeddings, dim=0), dim=0)
    return mean_embedding.squeeze().numpy()