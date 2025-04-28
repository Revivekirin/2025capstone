#!/bin/sh

# Tor Proxy가 이미 healthcheck 통과했으니, 바로 크롤링 시작
echo " curl 크롤러 시작"
apk add --no-cache curl
python crawl_with_curl.py
