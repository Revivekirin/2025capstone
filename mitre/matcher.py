from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from nlp.embedder import get_segmented_embedding
from nlp.embedder_st import get_embedding_st

def calculate_mire_embedding(techniques_with_names):
    print("Calculating MIRE embedding...")
    mitre_embeddings_list = []
    valid_techniques = []

    for tid, name_or_desc in techniques_with_names:
        embedding = get_embedding_st(name_or_desc)
        if embedding is not None:
            mitre_embeddings_list.append(embedding)
            valid_techniques.append((tid, name_or_desc))
        else:
            print(f"Warning: No embedding found for technique {tid}: {name_or_desc}.")
    if not mitre_embeddings_list:
        print("Error: No valid embeddings found for MIRE techniques.")
        return None, []

    print(f"Calculated embeddings for {len(mitre_embeddings_list)} techniques.")
    return np.array(mitre_embeddings_list), valid_techniques



def match_articles_to_mitre(articles_list, mitre_embeddings_array, techniques_info):
    if mitre_embeddings_array is None or len(techniques_info) == 0:
        print("No valid MIRE embeddings found. Skipping matching.")
        for article in articles_list:
            article['mitre_match']=None
        return articles_list
    print("Matching articles to MIRE techniques...")
    matched_articles = []
    for i, article in enumerate(articles_list):
        print(f"Processing article {i+1}/{len(articles_list)}: {article['title']}")

        article_content_embedding = get_embedding_st(article["content"])
        if article_content_embedding is None:
            print(f"Warning: No embedding found for article {i+1}: {article['title']}.")
            article['mitre_match'] = None
            matched_articles.append(article)
            continue

        try:
            similarities = cosine_similarity([article_content_embedding], mitre_embeddings_array)[0]
            best_match_index = np.argmax(similarities)

            matched_id, matched_name = techniques_info[best_match_index]
            match_score = float(similarities[best_match_index])

            article['mitre_match'] = {
                "id": matched_id,
                "name": matched_name,
                "score": match_score,
            }
            print(f"Matched with technique {matched_id}: {matched_name} (score: {match_score})")
        except Exception as e:
            print(f"Error matching article {i+1}: {e}")
            article['mitre_match'] = None
        
        matched_articles.append(article)

    print("Matching completed.")
    return matched_articles
