FROM mcr.microsoft.com/playwright:v1.51.1-jammy

WORKDIR /app

RUN npm init -y
RUN npm install playwright@1.51.1
RUN npm install axios

COPY . .

CMD ["bash", "-c", "node crawl_ransomewatch.js && sleep infinity"]
