#!/bin/bash
echo "[$(date)] 📦 playwright-crawler 실행 시작"

cd /home/capstone-design/Downloads/2025capstone  || exit 1
#scd /Users/kimjihe/Desktop/git/2025capstone || exit 1

# Docker 이미지 빌드
docker-compose up -d playwright-crawler

# 각 크롤링 실행
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-playwright-crawler node crawl_gbhackers.js
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-playwright-crawler node crawl_security_affairs.js
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-playwright-crawler node crawl_thehackernews.js
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-playwright-crawler node crawl_security_week.js
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-playwright-crawler node crawl_boannews.js
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-playwright-crawler node crawl_ransomewatch.js

echo "[$(date)] playwright-crawler 실행 완료"
