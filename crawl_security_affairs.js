const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');

const baseUrls = [
  'https://securityaffairs.com/category/cyber-crime',
  'https://securityaffairs.com/category/cyber-warfare-2',
  'https://securityaffairs.com/category/apt',
  'https://securityaffairs.com/category/data-breach',
  'https://securityaffairs.com/category/deep-web',
  'https://securityaffairs.com/category/digital-id',
  'https://securityaffairs.com/category/hacking',
  'https://securityaffairs.com/category/hacktivism'
];

const downloadImage = (url, filepath) => {
  return new Promise((resolve, reject) => {
    if (url.endsWith('.svg')) return resolve(); // SVG 무시
    https.get(url, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`이미지 다운로드 실패 (${res.statusCode})`));
      }
      const fileStream = fs.createWriteStream(filepath);
      res.pipe(fileStream);
      fileStream.on('finish', () => fileStream.close(resolve));
    }).on('error', reject);
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true });

  for (const baseUrl of baseUrls) {
    const page = await browser.newPage();
    console.log(`\n🌐 카테고리: ${baseUrl}\n`);
    await page.goto(baseUrl, { waitUntil: 'load' });

    const categoryName = baseUrl.split('/').filter(Boolean).pop(); // 마지막 path만 추출

    const rawArticles = await page.$$eval('div.news-card h5 > a', (anchors) => {
      const seen = new Set();
      return anchors
        .map(a => ({
          title: a.innerText.trim(),
          url: a.href
        }))
        .filter(a => a.title && a.url && !seen.has(a.url) && seen.add(a.url));
    });

    if (rawArticles.length === 0) {
      console.warn(`⚠️ [${categoryName}] 수집된 기사가 없습니다.`);
      await page.close();
      continue;
    }

    if (rawArticles.length < 3) {
      console.warn(`⚠️ [${categoryName}] 기사 수 부족: ${rawArticles.length}개만 수집됨 (요청: 3개)`);
    }

    const articles = rawArticles.slice(0, 3);
    console.log(`📰 [${categoryName}] 수집된 기사 ${articles.length}개\n`);

    for (const [i, article] of articles.entries()) {
      const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
      const articleDir = path.join(__dirname, 'downloads', categoryName, `${i + 1}_${safeTitle}`);
      fs.mkdirSync(articleDir, { recursive: true });

      console.log(`📄 [${i + 1}] ${article.title}`);
      console.log(`🔗 URL: ${article.url}`);

      const articlePage = await browser.newPage();
      await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

      let content = '', images = [];

      try {
        content = await articlePage.$eval('div.article-details-block', el => el.innerText.trim());

        images = await articlePage.$$eval('div.article-details-block img', imgs =>
          imgs
            .map(img => img.src)
            .filter(src => src && src.startsWith('http') && !src.endsWith('.svg'))
        );

        const fullText = `
제목: ${article.title}
URL: ${article.url}

${content}
        `.trim();

        fs.writeFileSync(path.join(articleDir, 'article.txt'), fullText, 'utf-8');
        console.log(`📝 기사 본문 저장 완료`);
      } catch (e) {
        console.log(`⚠️ 본문 수집 실패: ${e.message}`);
        fs.writeFileSync(path.join(articleDir, 'article.txt'), '(본문 없음)', 'utf-8');
      }

      if (images.length > 0) {
        console.log(`🖼️ 이미지 ${images.length}개 다운로드 중...`);
        for (const [idx, imgUrl] of images.entries()) {
          const ext = path.extname(new URL(imgUrl).pathname).split('?')[0] || '.jpg';
          const filename = path.join(articleDir, `image_${idx + 1}${ext}`);
          try {
            await downloadImage(imgUrl, filename);
            console.log(`   ✅ 저장 완료: ${filename}`);
          } catch (err) {
            console.log(`   ❌ 실패: ${imgUrl}`);
          }
        }
      } else {
        console.log(`🖼️ 저장할 이미지 없음`);
      }

      await articlePage.close();
      console.log('-'.repeat(80));
    }

    await page.close();
  }

  await browser.close();
})();
