# Playwright Crawler

This is a simple Playwright-based web crawler wrapped in Docker.

✅ **Tested on:** macOS with M2 chip  
⚠️ If you encounter issues on a different OS, feel free to message me on KakaoTalk.

## 🚀 Getting Started

After launching **Docker Desktop**, run the following commands in your terminal:

```bash
# Crawling: gbhackers, security_affairs, thehackernews, securityweek, ransomewatch
chmod +x run_playwright.sh
./scripts/run_playwright.sh

# Crawling: bleeping_computer
chmod +x run_node.sh
./scripts/run_node.sh

# crawl darkweb .html from proxy server
chmod +x run_compose.sh
./scripts/run_compose.sh

```

KEYWORD should be the name of a ransomware group (e.g., `babuk`, `lockbit`, etc.)

The crawler will save the results as `.txt` and `.png` files in the following path:

`/app/downloads`
