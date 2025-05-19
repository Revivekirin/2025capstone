#!/bin/bash
echo "[$(date)] 📦 node-crawler 실행 시작"

cd /home/capstone-design/Downloads/2025capstone || exit 1
# cd /Users/kimjihe/Desktop/git/2025capstone || exit 1

# Docker 이미지 빌드 및 실행 
docker-compose up -d node-crawler

# 크롤링 실행
docker run --rm -v "$PWD/downloads:/app/downloads" 2025capstone-node-crawler node crawl_bleeping_computer.js

echo "[$(date)] node-crawler 실행 완료"
