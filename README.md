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
docker run --rm -e KEYWORD=babuk -v $(pwd)/downloads:/app/downloads playwright-crawler

KEYWORD should be the name of a ransomware group (e.g., babuk, lockbit, etc.)

The crawler will save the results as .txt and .png files in the following path:

```bash
/app/downloads