const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const keyword = process.env.KEYWORD || 'ransomware';
const searchUrl = `https://gbhackers.com/?s=${encodeURIComponent(keyword)}`;

const downloadImage = (url, filepath) => {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    mod.get(url, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`Failed to get '${url}' (${res.statusCode})`));
      }
      const fileStream = fs.createWriteStream(filepath);
      res.pipe(fileStream);
      fileStream.on('finish', () => fileStream.close(resolve));
    }).on('error', reject);
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(searchUrl, { waitUntil: 'networkidle' });

  // 기사 목록 수집
  let articles = await page.$$eval('h3.entry-title > a', links =>
    links.map(link => ({
      title: link.textContent.trim(),
      url: link.href
    }))
  );

  // 최신 기사 3개로 제한
  articles = articles.slice(0, 3);

  console.log(`🔎 검색어 "${keyword}"에 대한 최신 기사 3개 수집\n`);

  for (const [index, article] of articles.entries()) {
    const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const articleDir = path.join(__dirname, 'downloads', `${index + 1}_${safeTitle}`);
    fs.mkdirSync(articleDir, { recursive: true });

    console.log(`📄 [${index + 1}] ${article.title}`);
    console.log(`🔗 URL: ${article.url}`);

    const articlePage = await browser.newPage();
    await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000  });

    let content = '';
    try {
      content = await articlePage.$eval('div.td-post-content', el => el.innerText.trim());

      // 전체 기사 내용 저장 (제목 + URL 포함)
      const fullText = `
제목: ${article.title}
URL: ${article.url}

${content}
      `.trim();

      //article.txt 저장
      fs.writeFileSync(path.join(articleDir, 'article.txt'), fullText, 'utf-8');    
      console.log(`📝 전체 기사 내용:\n\n${fullText}\n`);
    } catch (e) {
      console.log(`📝 기사 내용을 찾을 수 없음 \n`);
      
      //article.txt 저장
      fs.writeFileSync(path.join(articleDir, 'article.txt'), '(본문을 찾을 수 없음)', 'utf-8');
    }

    // 이미지 저장
    const images = await articlePage.$$eval('div.td-post-content img', imgs =>
      imgs.map(img => img.getAttribute('data-src') || img.src)
          .filter(src => src && src.startsWith('http'))
    );

    if (images.length > 0) {
      console.log(`🖼️ 이미지 저장 중 (${images.length}개)...`);
      for (const [imgIdx, src] of images.entries()) {
        const ext = path.extname(new URL(src).pathname) || '.jpg';
        const filename = path.join(articleDir, `image_${imgIdx + 1}${ext}`);
        try {
          await downloadImage(src, filename);
          console.log(`   ✅ 저장됨: ${filename}`);
        } catch (err) {
          console.log(`   ❌ 실패: ${src}`);
        }
      }
    } else {
      console.log("🖼️ 저장할 이미지 없음");
    }

    console.log('\n' + '-'.repeat(100) + '\n');
    await articlePage.close();
  }

  await browser.close();
  // 절대 resolve 되지 않음
})();
