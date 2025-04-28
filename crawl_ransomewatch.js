const { chromium } = require('playwright');
const axios = require('axios');
const fs = require('fs');

async function runCrawler() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://ransomwatch.telemetry.ltd/#/recentposts', {
    waitUntil: 'domcontentloaded',
  });

  await page.waitForTimeout(5000);
  const today = new Date().toISOString().slice(0, 10);

  const groups = await page.evaluate((today) => {
    const rows = Array.from(document.querySelectorAll('tbody tr'));
    const matchingGroups = [];

    for (const row of rows) {
      const dateCell = row.querySelector('td');
      const groupCell = row.querySelectorAll('td')[2];

      if (dateCell && dateCell.textContent.trim() === today && groupCell) {
        matchingGroups.push(groupCell.textContent.trim());
      }
    }

    return [...new Set(matchingGroups)];
  }, today);

  await browser.close();

  if (groups.length === 0) {
    console.log(`[${today}] 기준 그룹이 없습니다.`);
    return;
  }

  console.log(`Groups listed on ${today}:`, groups);

  const groupsWithFqdn = [];

  for (const group of groups) {
    console.log(`\n--- ${group} ---`);
    const fqdn = await getLatestOnionFQDN(group);

    if (!fqdn) {
      console.log(`❌ ${group}: 사용할 수 있는 .onion 주소가 없습니다.`);
      continue;
    }

    console.log(`🧅 ${group} 최신 FQDN: ${fqdn}`);
    groupsWithFqdn.push({ group, fqdn });
  }

  const outputPath = '/app/downloads/onion_list.json';
  fs.writeFileSync(outputPath, JSON.stringify(groupsWithFqdn, null, 2));
  console.log(`📦 저장 완료: ${outputPath}`);
}

async function getLatestOnionFQDN(groupName) {
  try {
    const res = await axios.get('https://ransomwhat.telemetry.ltd/groups');
    const parsed = res.data;
    const target = parsed.find(g => g.name === groupName);
    if (!target || !target.locations) return null;

    const sorted = target.locations
      .filter(loc => loc.fqdn.endsWith('.onion') && loc.enabled)
      .sort((a, b) => new Date(b.updated) - new Date(a.updated));

    return sorted[0]?.fqdn || null;
  } catch (err) {
    console.error(`[ERROR] ${groupName} FQDN 요청 실패:`, err.message);
    return null;
  }
}

async function loop() {
  while (true) {
    console.log(`\nPlaywright 크롤러 실행`);
    await runCrawler();
    console.log(`Playwright 크롤링 완료, 다음 실행까지 대기`);

    await new Promise(resolve => setTimeout(resolve, 10 * 60 * 1000)); // 10분마다
  }
}

loop();
