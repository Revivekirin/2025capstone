#!/bin/bash

echo "playwright 크롤러 시작: $1"

case "$1" in
  gbhackers)
    node crawl_gbhackers.js
    ;;
  securityaffairs)
    node crawl_security_affairs.js
    ;;
  ransomewatch)
    node crawl_ransomewatch.js
    ;;
  *)
    echo "알 수 없는 크롤러: $1"
    exit 1
    ;;
esac
