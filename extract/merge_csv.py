import pandas as pd
from pathlib import Path
from datetime import datetime

# CSV 파일들이 있는 디렉토리 경로
csv_dir = Path("~/downloads/extract")  # 경로 수정 필요
csv_files = list(csv_dir.glob("*.csv"))
today_str = datetime.now().strftime("%Y%m%d")

# 모든 CSV 파일 병합
all_dfs = []
for csv_file in csv_files:
    df = pd.read_csv(csv_file)
    all_dfs.append(df)

# 하나의 DataFrame으로 병합
merged_df = pd.concat(all_dfs, ignore_index=True)

# 중복 행 제거 (완전히 동일한 행 기준)
dedup_df = merged_df.drop_duplicates()

# 결과 저장
dedup_df.to_csv(f"{today_str}.csv", index=False, encoding='utf-8')
print(f"[✓] 병합 및 중복 제거 완료: {len(dedup_df)} rows saved to merged_deduplicated.csv")
