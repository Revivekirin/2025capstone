const { chromium } = require('playwright');
const axios = require('axios');
const fs = require('fs');

// page.goto() (retry 추가)
async function safeGoto(page, url, options = {}, retries = 3, delayMs = 5000) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`[GOTO] ${url} (시도 ${attempt}/${retries})`);
      await page.goto(url, options);
      console.log(`[GOTO] 성공`);
      return;
    } catch (err) {
      console.error(`[GOTO 실패] ${err.message}`);
      if (attempt === retries) throw err;
      console.log(`[대기 후 재시도] ${delayMs / 1000}초`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
}

async function runCrawler() {
  console.log(`[▶] Playwright 시작`);

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();

  await safeGoto(page, 'https://ransomwatch.telemetry.ltd/#/recentposts', {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  await page.waitForTimeout(5000);
  const today = new Date().toISOString().slice(0, 10);
  //const today = "2025-04-28"; 

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

  const outputPath = '/app/downloads/onion_list.json';
  let existingData = [];

  if (fs.existsSync(outputPath)) {
    try {
      existingData = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    } catch (err) {
      console.error("[ERROR] 기존 JSON 파일 읽기 실패:", err.message);
    }
  }

  // 기존 데이터: group → fqdn
  const existingMap = {};
  for (const item of existingData) {
    existingMap[item.group] = item.fqdn;
  }

  // 업데이트 처리
  for (const group of groups) {
    console.log(`\n--- ${group} ---`);
    const fqdn = await getLatestOnionFQDN(group);

    if (!fqdn) {
      console.log(`❌ ${group}: 사용할 수 있는 .onion 주소가 없습니다.`);
      continue;
    }

    const previousFqdn = existingMap[group];
    if (previousFqdn && previousFqdn !== fqdn) {
      console.log(`🔄 ${group}의 FQDN이 변경됨: ${previousFqdn} → ${fqdn}`);
      // 업데이트
      const index = existingData.findIndex(item => item.group === group);
      if (index !== -1) {
        existingData[index].fqdn = fqdn;
      }
    } else if (!previousFqdn) {
      console.log(`➕ ${group} 신규 등록`);
      existingData.push({ group, fqdn });
    } else {
      console.log(`✅ ${group} 기존 FQDN 유지`);
    }
  }

  fs.writeFileSync(outputPath, JSON.stringify(existingData, null, 2));
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

// 🌀 최종 실행 부분
async function main() {
  console.log(`[▶] Playwright 크롤러 시작`);
  await runCrawler();
}

main();
