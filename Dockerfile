FROM mcr.microsoft.com/playwright:v1.51.1-jammy

WORKDIR /app

# 필요시 패키지 초기화 (이미지에 node 포함되어 있음)
RUN npm init -y

# Playwright 설치 (1.51 고정)
RUN npm install playwright@1.51.1

COPY . .

CMD ["node", "crawl.js"]
