#!/bin/sh

echo "curl 크롤러 시작"
apk add --no-cache curl
python crawl_with_curl.py
