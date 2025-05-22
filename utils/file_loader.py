import os
import pandas as pd

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

                    rel_path = os.path.relpath(root, base_dir)
                    source = rel_path.split(os.sep)[0]

                    news_list.append({
                        'title': title,
                        'content': body,
                        'source': source,
                    })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    print(f"Loaded {len(news_list)} articles.")
    return news_list


def load_mitre_techniques(xlsx_path):
    print(f"Loading MITRE techniques from: {xlsx_path}")
    try:
        df = pd.read_excel(xlsx_path)
        if 'ID' not in df.columns or 'name' not in df.columns:
            if 'ID' in df.columns and 'description' in df.columns and 'name' not in df.columns:
                print("Warning: 'name' column not found. Using 'description' as name.")
                teqchniques = list(zip(df['ID'], df['description']))
            else:
                raise ValueError("MIRE ATT&CK data must contain 'ID and 'name (or 'description') columns." )
        else:
            techniques = list(zip(df['ID'], df['name']))

        print(f"Loaded {len(techniques)} techniques.")
        return techniques
    except FileNotFoundError:
        print(f"File not found: {xlsx_path}")
        return []
    except Exception as e:
        print(f"Error loading {xlsx_path}: {e}")
        return []
