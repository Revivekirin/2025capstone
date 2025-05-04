#!/bin/bash
echo "[$(date)] 🧱 docker-compose 시작"

cd /home/사용자/2025capstone || exit 1
docker-compose up -d

echo "[$(date)] ✅ docker-compose 완료"
