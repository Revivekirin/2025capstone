const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    javaScriptEnabled: true,
    locale: 'en-US'
  });

  const page = await context.newPage();

  // ❗ navigator.webdriver = false 로 위장
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', {
      get: () => false,
    });
  });

  try {
    console.log('🌐 TheHackerNews 접속 중 (stealth 모드)...');
    await page.goto('https://www.securityweek.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });

    const title = await page.title();
    console.log(`✅ 페이지 제목: ${title}`);

    const bodyHtml = await page.content();
    console.log(`📦 body 길이: ${bodyHtml.length} chars`);

    if (bodyHtml.includes('story-link') || bodyHtml.includes('home-title')) {
      console.log('✅ 주요 기사 요소가 로드됨 ✔');
    } else {
      console.log('⚠️ 주요 기사 요소가 DOM에 없음 (우회 실패 또는 구조 변경)');
    }

    await page.screenshot({ path: 'stealth_debug.png', fullPage: true });
    console.log('📸 스크린샷 저장: stealth_debug.png');
  } catch (err) {
    console.error('❌ 오류 발생:', err.message);
  } finally {
    await browser.close();
  }
})();
