const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');

const baseUrls = [
  'https://securityaffairs.com/',
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
    if (url.endsWith('.svg')) return resolve();
    https.get(url, (res) => {
      if (res.statusCode !== 200) return reject(new Error(`이미지 다운로드 실패 (${res.statusCode})`));
      const fileStream = fs.createWriteStream(filepath);
      res.pipe(fileStream);
      fileStream.on('finish', () => fileStream.close(resolve));
    }).on('error', reject);
  });
};

const getTodayString = () => {
  const today = new Date();
  const options = { year: 'numeric', month: 'long', day: '2-digit' };
  return today.toLocaleDateString('en-US', options);
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const todayStr = getTodayString();
  console.log(`📅 오늘 날짜: ${todayStr}`);

  for (const baseUrl of baseUrls) {
    let pageNum = 1;
    let foundTodayArticle = false;
    const categoryName = baseUrl.split('/').filter(Boolean).pop() || 'main';

    while (!foundTodayArticle) {
      let url = baseUrl;
      if (pageNum > 1) {
        if (baseUrl === 'https://securityaffairs.com/') {
          url = `https://securityaffairs.com/?page=${pageNum}#latest_news_section`;
        } else {
          url = `${baseUrl}/page/${pageNum}`;
        }
      }

      const page = await browser.newPage();
      console.log(`\n🌐 카테고리: ${url}`);
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 60000 });
      } catch (err) {
        console.log(`❌ 페이지 로드 실패: ${err.message}`);
        await page.close();
        break;
      }

      const todaysArticles = await page.evaluate((todayStr) => {
        const results = [];

        document.querySelectorAll('div.banner-content').forEach(node => {
          const dateEl = node.querySelector('p.date');
          const linkEl = node.querySelector('h1 a');
          if (dateEl && linkEl && dateEl.textContent.trim() === todayStr) {
            results.push({ title: linkEl.textContent.trim(), url: linkEl.href });
          }
        });

        document.querySelectorAll('div.sngl-article').forEach(node => {
          const dateSpan = node.querySelector('.post-time span');
          const linkEl = node.querySelector('h6 > a');
          if (dateSpan && linkEl && dateSpan.textContent.trim() === todayStr) {
            results.push({ title: linkEl.textContent.trim(), url: linkEl.href });
          }
        });

        document.querySelectorAll('div.news-card-cont').forEach(node => {
          const spans = node.querySelectorAll('.post-time span');
          const dateSpan = Array.from(spans).find(span => /[A-Za-z]+ \d{2}, \d{4}/.test(span.textContent));
          const linkEl = node.querySelector('h5 a');
          if (dateSpan && linkEl && dateSpan.textContent.trim() === todayStr) {
            results.push({ title: linkEl.textContent.trim(), url: linkEl.href });
          }
        });

        return results;
      }, todayStr);

      if (todaysArticles.length === 0) {
        console.log(`⚠️ [${categoryName}] ${pageNum} 페이지에서 오늘 날짜 기사 없음`);
        await page.close();
        pageNum++;
        if (pageNum > 3) break; // 최대 페이지 순회 제한
        continue;
      }

      foundTodayArticle = true;
      console.log(`📰 [${categoryName}] 오늘 날짜 기사 ${todaysArticles.length}건 수집`);

      for (const [i, article] of todaysArticles.entries()) {
        const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
        const articleDir = path.join(
          __dirname,
          'downloads',
          'security_affairs',
          todayStr,
          `${categoryName}_${i + 1}_${safeTitle}`
        );
        fs.mkdirSync(articleDir, { recursive: true });

        console.log(`📄 [${i + 1}] ${article.title}`);
        console.log(`🔗 URL: ${article.url}`);

        const articlePage = await browser.newPage();
        await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

        let content = '', images = [];

        try {
          content = await articlePage.$eval('div.article-details-block', el => el.innerText.trim());
          images = await articlePage.$$eval('div.article-details-block img', imgs =>
            imgs.map(img => img.src).filter(src => src && src.startsWith('http') && !src.endsWith('.svg'))
          );

          const fullText = `\n제목: ${article.title}\nURL: ${article.url}\n\n${content}`.trim();
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
  }

  await browser.close();
})();