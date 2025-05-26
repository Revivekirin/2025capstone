#!/bin/bash
echo "[$(date)] node-crawler 실행 시작"

#cd /home/capstone-design/Downloads/2025capstone || exit 1
cd /Users/kimjihe/Desktop/git/2025capstone || exit 1

TODAY=$(date +%Y-%m-%d)
BASE_DIR="./downloads"
SITES=("securityweek")

echo "[$(date)] 🧹 이전 날짜 디렉토리 삭제 중..."
for SITE in "${SITES[@]}"; do
    SITE_DIR="$BASE_DIR/$SITE"
    if [ -d "$SITE_DIR" ]; then
        find "$SITE_DIR" -mindepth 1 -maxdepth 1 -type d ! -name "$TODAY" -exec rm -rf {} +
        echo " - $SITE: 이전 날짜 삭제 완료"
    fi
done

# Docker 이미지 빌드 및 실행 
docker-compose up -d node-crawler

# 크롤링 실행
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-node-crawler node crawl_bleeping_computer.js

echo "[$(date)] node-crawler 실행 완료"
