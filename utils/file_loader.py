import os
import pandas as pd
from datetime import datetime

from datetime import datetime

def load_articles_from_directory(base_dir):
    news_list = []
    print(f"Loading articles from: {base_dir}")
    
    for root, _, files in os.walk(base_dir):
        if 'article.txt' in files:
            file_path = os.path.join(root, 'article.txt')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                lines = content.splitlines()
                title_line = next((line for line in lines if line.startswith("제목: ")), None)

                if title_line:
                    title = title_line.replace("제목: ", "").strip()
                    try:
                        url_line_index = lines.index(next(line for line in lines if line.startswith("URL: ")))
                        content_start_index = url_line_index + 1
                    except (StopIteration, ValueError):
                        content_start_index = lines.index(title_line) + 2

                    body = "\n".join(lines[content_start_index:]).strip()

                    # 상대 경로에서 source 추출
                    rel_path = os.path.relpath(root, base_dir)
                    path_parts = rel_path.split(os.sep)
                    source = path_parts[0] if len(path_parts) > 0 else "unknown"

                    # 날짜 디렉토리 추출
                    date_str = path_parts[1] if len(path_parts) > 1 else None
                    formatted_date = ""

                    if date_str:
                        for fmt in ("%B %d, %Y", "%Y-%m-%d"):
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                formatted_date = parsed_date.strftime("%Y-%m-%d")
                                break
                            except ValueError:
                                continue
                        if not formatted_date:
                            print(f"  [!] 날짜 변환 실패: {date_str} (지원되지 않는 형식)")

                    news_list.append({
                        'title': title,
                        'content': body,
                        'date': formatted_date,
                        'source': source,
                    })

            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    print(f"Loaded {len(news_list)} articles.")
    return news_list