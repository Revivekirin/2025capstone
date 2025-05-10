const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');
const https = require('https');

const BASE_URL = 'https://www.bleepingcomputer.com/news/security/';
const getTodayUSDate = () =>
  new Date().toLocaleDateString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric'
  }); 

const downloadImage = (url, filepath) => new Promise((resolve, reject) => {
  https.get(url, (res) => {
    if (res.statusCode !== 200) return reject(new Error(`이미지 다운로드 실패: ${url}`));
    const stream = fs.createWriteStream(filepath);
    res.pipe(stream);
    stream.on('finish', () => stream.close(resolve));
  }).on('error', reject);
});

(async () => {
  const todayDate = getTodayUSDate();
  const response = await axios.get(BASE_URL);
  const $ = cheerio.load(response.data);
  let collected = 0;

  $('li').each(async (_, li) => {
    const dateText = $(li).find('li.bc_news_date').text().trim();
    if (dateText !== todayDate) return;

    const titleEl = $(li).find('h4 a');
    const url = titleEl.attr('href');
    const title = titleEl.text().trim();

    // 외부 링크(external sponsor 등) 제외: bleepingcomputer.com 도메인만 허용
    if (!url || !url.startsWith('https://www.bleepingcomputer.com/news/security/')) return;

    const imageUrl = $(li).find('.bc_latest_news_img img').attr('src') || '';
    const summary = $(li).find('p').first().text().trim();

    const safeTitle = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const articleDir = path.join(__dirname, 'downloads', `${++collected}_${safeTitle}`);
    fs.mkdirSync(articleDir, { recursive: true });

    // 본문 가져오기: <div class="articleBody"> 내 모든 <p> 텍스트
    let articleContent = '';
    try {
      const articleRes = await axios.get(url);
      const $$ = cheerio.load(articleRes.data);
      articleContent = $$('.articleBody p')
        .map((i, el) => $$(el).text().trim())
        .get()
        .filter(p => p.length > 0)
        .join('\n\n');
    } catch (err) {
      articleContent = '(본문 수집 실패)';
    }

    const textContent = `제목: ${title}\nURL: ${url}\n날짜: ${todayDate}\n\n요약: ${summary}\n\n본문:\n${articleContent}`;
    fs.writeFileSync(path.join(articleDir, 'article.txt'), textContent, 'utf-8');

    // 이미지 저장
    if (imageUrl.startsWith('http')) {
      const ext = path.extname(new URL(imageUrl).pathname) || '.jpg';
      const imgPath = path.join(articleDir, `image_1${ext}`);
      try {
        await downloadImage(imageUrl, imgPath);
        console.log(`🖼️  이미지 저장됨: ${imgPath}`);
      } catch (e) {
        console.warn(`⚠️  이미지 다운로드 실패: ${imageUrl}`);
      }
    }

    console.log(`수집 완료: ${title}`);
  });
})();