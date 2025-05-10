const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');

const BASE_URLS = [
  { url: 'https://thehackernews.com/', category: 'main' },
  { url: 'https://thehackernews.com/search/label/Cyber%20Attack', category: 'cyber_attack' },
  { url: 'https://thehackernews.com/search/label/Vulnerability', category: 'vulnerability' }
];

const todayStr = new Date('2025-05-09').toISOString().split('T')[0];

const downloadImage = (url, filepath) => {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      if (res.statusCode !== 200) return reject(new Error(`이미지 다운로드 실패: ${res.statusCode}`));
      const fileStream = fs.createWriteStream(filepath);
      res.pipe(fileStream);
      fileStream.on('finish', () => fileStream.close(resolve));
    }).on('error', reject);
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    javaScriptEnabled: true,
    locale: 'en-US'
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  for (const { url: baseUrl, category } of BASE_URLS) {
    const page = await context.newPage();
    try {
      console.log(`🌐 [${category}] 방문 중: ${baseUrl}`);
      await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

      const articles = await page.$$eval('div.body-post.clear', nodes =>
        nodes.slice(0, 4).map(node => {
          const linkEl = node.querySelector('a.story-link');
          const titleEl = node.querySelector('h2.home-title');
          const imgEl = node.querySelector('.img-ratio img');
          if (!linkEl || !titleEl) return null;

          return {
            title: titleEl.textContent.trim(),
            url: linkEl.href,
            thumbImg: imgEl?.src || ''
          };
        }).filter(Boolean)
      );

      console.log(`📰 [${category}] 기사 ${articles.length}건 확인`);

      for (const [i, article] of articles.entries()) {
        const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
        const articleDir = path.join(
          __dirname,
          'downloads',
          'thehackernews',
          todayStr,
          `${category}_${i + 1}_${safeTitle}`
        );

        const articlePage = await context.newPage();
        await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

        let actualDateText = '';
        try {
          actualDateText = await articlePage.$eval('div.postmeta span.author', el => el.textContent.trim());
        } catch {
          console.warn(`⚠️ 날짜 추출 실패 - ${article.url}`);
          await articlePage.close();
          continue;
        }

        const parsedDate = new Date(actualDateText + ' 00:00:00').toISOString().split('T')[0];
        if (parsedDate !== todayStr) {
          console.log(`⏭️ [${category}] ${article.title} (본문 날짜: ${actualDateText})`);
          await articlePage.close();
          continue;
        }

        console.log(`✅ [${category}] 수집 중: ${article.title}`);

        let paragraphs = [];
        try {
          paragraphs = await articlePage.$$eval('div.articlebody p', nodes =>
            nodes.map(p => p.textContent.trim()).filter(p => p.length > 0)
          );
        } catch {
          console.warn('⚠️ 본문 <p> 수집 실패');
        }

        if (paragraphs.length === 0) {
          console.log(`⚠️ 본문 없음 → 기사 저장 생략: ${article.title}`);
          await articlePage.close();
          continue;
        }

        fs.mkdirSync(articleDir, { recursive: true });

        const fullText = `제목: ${article.title}\nURL: ${article.url}\n날짜: ${actualDateText}\n\n본문:\n${paragraphs.join('\n\n')}`;
        fs.writeFileSync(path.join(articleDir, 'article.txt'), fullText, 'utf-8');

        if (article.thumbImg?.startsWith('http')) {
          const ext = path.extname(new URL(article.thumbImg).pathname).split('?')[0] || '.jpg';
          const imgPath = path.join(articleDir, `thumb${ext}`);
          try {
            await downloadImage(article.thumbImg, imgPath);
            console.log(`🖼️  썸네일 저장 완료: ${imgPath}`);
          } catch {
            console.warn(`❌ 썸네일 다운로드 실패: ${article.thumbImg}`);
          }
        }

        await articlePage.close();
        console.log('✅ 저장 완료\n' + '-'.repeat(80));
      }

      await page.close();
    } catch (err) {
      console.error(`❌ 오류 [${category}]:`, err.message);
      await page.close();
    }
  }

  await browser.close();
})();