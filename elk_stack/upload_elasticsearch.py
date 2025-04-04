import glob
import os
from datetime import datetime

from elasticsearch import Elasticsearch

# Docker 기반 Elasticsearch 접속 설정
es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", "password"))

def parse_txt_article(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    title = lines[0].replace("제목: ", "").strip() if len(lines) > 0 else ""
    url = lines[1].replace("URL: ", "").strip() if len(lines) > 1 else ""
    content = "".join(lines[3:]).strip() if len(lines) > 3 else ""

    return {
        "title": title,
        "url": url,
        "published_at": datetime.today().strftime("%Y-%m-%d"),
        "source": "GBHackers",
        "tags": [],
        "summary": content[:300],
        "content": content
    }

def upload_articles_to_es(base_dir="downloads"):
    txt_files = glob.glob(os.path.join(base_dir, "**", "*.txt"), recursive=True)
    print(f"총 {len(txt_files)}개의 기사 파일을 찾았습니다.\n")

    for file_path in txt_files:
        article_doc = parse_txt_article(file_path)

        if not article_doc["title"] or not article_doc["url"]:
            print(f"스킵됨 (필수 정보 없음): {file_path}")
            continue

        res = es.index(index="security_news", document=article_doc)
        print(f"업로드 완료: {article_doc['title']}")
        print(f"   📎 {article_doc['url']}\n")

if __name__ == "__main__":
    upload_articles_to_es()