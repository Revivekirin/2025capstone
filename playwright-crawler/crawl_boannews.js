const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'https://www.boannews.com';

const getTodayStr = () => {
  const now = new Date(); 
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const today = getTodayStr();

  const home = await context.newPage();
  await home.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });

  const baseUrls = await home.$$eval('#main_menu_hash a[href]', as =>
    as.map(a => a.href.trim()).filter(href =>
      href.includes('boannews.com/media/') || href.includes('boannews.com/search/')
    )
  );
  await home.close();

  console.log(`🔍 수집된 카테고리: ${baseUrls.length}개\n`);

  for (const base of baseUrls) {
    console.log(`📁 [카테고리] ${base}`);
    let pageNum = 1;
    const todaysArticles = [];

    while (true) {
      const url = `${base}${base.includes('?') ? '&' : '?'}Page=${pageNum}`;
      const page = await context.newPage();
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });

      const articles = await page.$$eval('div.news_list, div.news_main', nodes => {
        return nodes.map(node => {
          const link = node.querySelector('a[href*="/media/view.asp"]');
          const title = node.querySelector('.news_txt, .news_main_title')?.innerText.trim() || '';
          const summary = node.querySelector('.news_content, .news_main_txt')?.innerText.trim() || '';

          let rawDate = '';
          const writerSpan = node.querySelector('.news_writer');
          if (writerSpan) {
            const match = writerSpan.textContent.match(/\d{4}년\s*\d{1,2}월\s*\d{1,2}일/);
            if (match) rawDate = match[0];
          } else {
            const textContent = node.innerText || '';
            const dateMatch = textContent.match(/\d{4}년\s*\d{1,2}월\s*\d{1,2}일/);
            rawDate = dateMatch ? dateMatch[0] : '';
          }

          return {
            title,
            summary,
            href: link?.href,
            rawDate
          };
        }).filter(a => a.href);
      });

      let hasToday = false;
      for (const a of articles) {
        let date = a.rawDate;
        if (date) {
          date = date.replace(/년|월/g, '-').replace(/일/, '').replace(/\s/g, '').trim();
        }

        if (date === today) {
          hasToday = true;
          todaysArticles.push({ ...a, date });
        }
      }

      await page.close();

      if (!hasToday || articles.length === 0) break;
      pageNum++;
    }

    console.log(`📰 오늘 기사 수: ${todaysArticles.length}개\n`);

    for (const [i, article] of todaysArticles.entries()) {
      const page2 = await context.newPage();
      await page2.goto(article.href, { waitUntil: 'domcontentloaded' });

      let content = '';
      try {
        content = await page2.$eval('#news_content', el => el.innerText.trim());
      } catch {
        content = '(본문 없음)';
      }

      const safeTitle = article.title.replace(/[^a-z0-9가-힣]/gi, '_').replace(/_+/g, '_').slice(0, 80);
      const dir = path.join(__dirname, 'downloads', 'boannews', today, `${i + 1}_${safeTitle}`);
      fs.mkdirSync(dir, { recursive: true });

      fs.writeFileSync(
        path.join(dir, 'article.txt'),
        `제목: ${article.title}\nURL: ${article.href}\n날짜: ${article.date}\n\n요약: ${article.summary}\n\n본문:\n${content}`,
        'utf-8'
      );
      console.log(`📄 저장 완료: ${article.title}`);

      await page2.close();
    }

    console.log('-'.repeat(80));
  }

  await browser.close();
})();
