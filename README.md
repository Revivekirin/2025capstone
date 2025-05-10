# Playwright Crawler

This is a simple Playwright-based web crawler wrapped in Docker.

✅ **Tested on:** macOS with M2 chip  
⚠️ If you encounter issues on a different OS, feel free to message me on KakaoTalk.

## 🚀 Getting Started

After launching **Docker Desktop**, run the following commands in your terminal:

```bash
# Build the Docker image
docker build -t playwright-crawler .

# Run the container with your desired keyword
#docker run --rm -e KEYWORD=babuk -v $(pwd)/downloads:/app/downloads playwright-crawler
# gbhackers
docker run --rm -v "$PWD/downloads:/app/downloads" playwright-crawler node crawl_gbhackers.js

# security affairs
docker run --rm -v "$PWD/downloads:/app/downloads" playwright-crawler node crawl_security_affairs.js

# crawl ransomwatch recent post
docker run --rm -v "$PWD/downloads:/app/downloads" playwright-crawler node crawl_ransomewatch.js

# crawl darkweb .html from proxy server
docker compose up

```

KEYWORD should be the name of a ransomware group (e.g., `babuk`, `lockbit`, etc.)

The crawler will save the results as `.txt` and `.png` files in the following path:

`/app/downloads`
