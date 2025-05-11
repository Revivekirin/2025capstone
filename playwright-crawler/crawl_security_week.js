const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');

const todayStr = new Date('2025-05-09').toISOString().split('T')[0];

const BASE_URL = 'https://www.securityweek.com/';

const downloadImage = (url, filepath) => {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      if (res.statusCode !== 200) return reject(new Error(`이미지 다운로드 실패: ${res.statusCode}`));
      const stream = fs.createWriteStream(filepath);
      res.pipe(stream);
      stream.on('finish', () => stream.close(resolve));
    }).on('error', reject);
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    console.log(`🌐 SecurityWeek 접속: ${BASE_URL}`);
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

    // 오늘 날짜 기사만 필터링
    const articles = await page.$$eval('article.zox-art-wrap', (nodes, todayStr) => {
      return nodes.map(node => {
        const titleEl = node.querySelector('h2.zox-s-title2');
        const linkEl = node.querySelector('a[rel="bookmark"]');
        const dateMeta = node.querySelector('meta[itemprop="dateModified"]');
        const summary = node.querySelector('p.zox-s-graph')?.innerText.trim() || '';
        const imgEl = node.querySelector('div.img-ratio img');

        const title = titleEl?.innerText.trim();
        const url = linkEl?.href;
        const date = dateMeta?.getAttribute('content') || '';
        const img = imgEl?.src;

        if (!title || !url || !date) return null;
        return { title, url, date, summary, img };
      }).filter(a => a && a.date === todayStr);
    }, todayStr);

    console.log(`📰 오늘 날짜 기사 수: ${articles.length}`);
    let count = 0;

    for (const article of articles) {
      count++;
      const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
      const articleDir = path.join(__dirname, 'downloads', 'securityweek', todayStr, `${count}_${safeTitle}`);
      fs.mkdirSync(articleDir, { recursive: true });

      console.log(`📄 수집 중: ${article.title}`);
      console.log(`🔗 ${article.url}`);

      const articlePage = await context.newPage();
      await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

        let paragraphs = [];
        try {
        paragraphs = await articlePage.$$eval('div.zox-post-body p', nodes =>
            nodes.map(p => p.textContent.trim()).filter(p => p.length > 0)
        );
        } catch {
        console.warn('⚠️ 본문 <p> 수집 실패');
        }


      const fullText = `제목: ${article.title}\nURL: ${article.url}\n날짜: ${article.date}\n\n요약: ${article.summary}\n\n본문:\n${paragraphs.join('\n\n') || '(본문 없음)'}`;
      fs.writeFileSync(path.join(articleDir, 'article.txt'), fullText, 'utf-8');

      if (article.img?.startsWith('http')) {
        const ext = path.extname(new URL(article.img).pathname).split('?')[0] || '.jpg';
        const imgPath = path.join(articleDir, `thumb${ext}`);
        try {
          await downloadImage(article.img, imgPath);
          console.log(`🖼️  썸네일 저장 완료: ${imgPath}`);
        } catch {
          console.warn(`❌ 이미지 다운로드 실패: ${article.img}`);
        }
      }

      await articlePage.close();
      console.log('✅ 저장 완료\n' + '-'.repeat(80));
    }
  } catch (err) {
    console.error(`❌ 오류 발생: ${err.message}`);
  } finally {
    await browser.close();
  }
})();
