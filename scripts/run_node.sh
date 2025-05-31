#!/bin/bash
echo "[$(date)] node-crawler 실행 시작"

#cd /home/capstone-design/Downloads/2025capstone || exit 1
cd /Users/kimjihe/Desktop/git/2025capstone || exit 1

TODAY=$(date +%Y-%m-%d)
BASE_DIR="./downloads"
SITES=("securityweek")

# === 날짜 기준 정리 ===
TODAY=$(date +%Y-%m-%d)
BASE_DIR="./downloads"
SITES=("gbhackers" "securityaffairs" "thehackernews" "securityweek" "boannews")

echo "[$(date)] 🧹 이전 날짜 디렉토리 삭제 중..."
for SITE in "${SITES[@]}"; do
    SITE_DIR="$BASE_DIR/$SITE"
    if [ -d "$SITE_DIR" ]; then
        for DIR in "$SITE_DIR"/*; do
            if [ -d "$DIR" ]; then
                BASENAME=$(basename "$DIR")
                
                # Try converting to standard format
                PARSED_DATE=$(date -jf "%B %d, %Y" "$BASENAME" +%Y-%m-%d 2>/dev/null || echo "$BASENAME")
                
                if [ "$PARSED_DATE" != "$TODAY" ]; then
                    rm -rf "$DIR"
                    echo " - $SITE: 삭제됨 → $BASENAME (변환된 날짜: $PARSED_DATE)"
                fi
            fi
        done
    fi
done

# Docker 이미지 빌드 및 실행 
docker-compose up -d node-crawler

# 크롤링 실행
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-node-crawler node crawl_bleeping_computer.js

echo "[$(date)] node-crawler 실행 완료"
