#!/bin/bash
echo "[$(date)] 📦 playwright-crawler 실행 시작"

cd /home/사용자/2025capstone || exit 1

# Docker 이미지 빌드
docker build -t playwright-crawler .

# 각 크롤링 실행
docker run --rm -v "$PWD/downloads:/app/downloads" playwright-crawler node crawl_gbhackers.js
docker run --rm -v "$PWD/downloads:/app/downloads" playwright-crawler node crawl_security_affairs.js
docker run --rm -v "$PWD/downloads:/app/downloads" playwright-crawler node crawl_ransomewatch.js

echo "[$(date)] ✅ playwright-crawler 실행 완료"
