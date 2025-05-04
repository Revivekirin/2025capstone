const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const urlsToCheck = [
  'https://gbhackers.com/',
  'https://gbhackers.com/category/threatsattacks/',
  'https://gbhackers.com/category/cyber-attack/',
  'https://gbhackers.com/category/data-breach/',
  'https://gbhackers.com/category/vulnerability-android-2/',
  'https://gbhackers.com/category/what-is/',
  'https://gbhackers.com/category/incident-response/',
  'https://gbhackers.com/category/top-10/',
];

const getTodayISODate = () => new Date().toISOString().split('T')[0];
// const getTodayISODate = () => {
//   const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
//   return yesterday.toISOString().split('T')[0];
// };


const downloadImage = (url, filepath) => {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    mod.get(url, (res) => {
      if (res.statusCode !== 200) return reject(new Error(`Failed to get '${url}' (${res.statusCode})`));
      const fileStream = fs.createWriteStream(filepath);
      res.pipe(fileStream);
      fileStream.on('finish', () => fileStream.close(resolve));
    }).on('error', reject);
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const todayDate = getTodayISODate();
  const seenUrls = new Set();
  let totalCollected = 0;

  for (const url of urlsToCheck) {
    console.log(`🌐 방문 중: ${url}`);
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });

      let articleLinks = [];
      if (url === 'https://gbhackers.com/') {
        articleLinks = await page.$$eval('div.td_module_10 h3.entry-title > a', links =>
          links.slice(0, 5).map(link => ({ url: link.href, title: link.textContent.trim() }))
        );
      } else {
        articleLinks = await page.$$eval('div.td-module-container h3.entry-title > a', links =>
          links.slice(0, 3).map(link => ({ url: link.href, title: link.textContent.trim() }))
        );
      }

      for (const article of articleLinks) {
        if (seenUrls.has(article.url)) continue;

        const articlePage = await browser.newPage();
        try {
          await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

          const articleDate = await articlePage.$eval('time.entry-date', el => el.getAttribute('datetime').split('T')[0]);
          if (url !== 'https://gbhackers.com/' && articleDate !== todayDate) {
            console.log(`⏭️ 오늘 날짜 아님 (${articleDate}) - ${article.url}`);
            await articlePage.close();
            continue;
          }

          seenUrls.add(article.url);
          const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
          const articleDir = path.join(__dirname, 'downloads', `${++totalCollected}_${safeTitle}`);
          fs.mkdirSync(articleDir, { recursive: true });

          console.log(`📄 ${article.title}`);
          console.log(`🔗 ${article.url}`);

          let content = '';
          try {
            content = await articlePage.$eval('div.td-post-content', el => el.innerText.trim());
          } catch {
            content = '(본문을 찾을 수 없음)';
          }

          fs.writeFileSync(path.join(articleDir, 'article.txt'), `제목: ${article.title}\nURL: ${article.url}\n\n${content}`, 'utf-8');

          const images = await articlePage.$$eval('div.td-post-content img', imgs =>
            imgs.map(img => img.getAttribute('data-src') || img.src).filter(src => src?.startsWith('http'))
          );

          for (const [idx, imgUrl] of images.entries()) {
            const ext = path.extname(new URL(imgUrl).pathname) || '.jpg';
            const imgPath = path.join(articleDir, `image_${idx + 1}${ext}`);
            try {
              await downloadImage(imgUrl, imgPath);
              console.log(`   🖼️ 저장됨: ${imgPath}`);
            } catch {
              console.warn(`   ❌ 이미지 실패: ${imgUrl}`);
            }
          }
        } catch (err) {
          console.error(`❌ 기사 처리 중 오류 발생: ${err.message}`);
        } finally {
          await articlePage.close();
          console.log('-'.repeat(80));
        }
      }
    } catch (err) {
      console.error(`❌ ${url} 방문 중 오류 발생: ${err.message}`);
    }
  }

  console.log(`\n✅ 오늘(${todayDate}) 수집된 기사 수: ${totalCollected}`);
  await browser.close();
})();