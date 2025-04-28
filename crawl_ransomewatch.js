// const { chromium } = require('playwright');
// const axios = require('axios');
// const fs = require('fs');


// // 🌀 Tor proxy ready check
// async function waitForTorProxyReady(maxRetries = 20, delayMs = 10000) {
//   for (let attempt = 1; attempt <= maxRetries; attempt++) {
//     try {
//       console.log(`[Tor Check] (${attempt}/${maxRetries})`);
//       const response = await axios.get('https://check.torproject.org/', {
//         proxy: {
//           host: '127.0.0.1',
//           port: 9050,
//           protocol: 'socks5'
//         },
//         timeout: 5000
//       });
//       if (response.status === 200) {
//         console.log(`[✓] Tor Proxy Ready!`);
//         return;
//       }
//     } catch (error) {
//       console.log(`[Waiting for Tor Proxy...]`);
//     }
//     await new Promise(resolve => setTimeout(resolve, delayMs));
//   }
//   console.error(`[✖] Tor Proxy not ready after ${maxRetries} attempts. Exiting.`);
//   process.exit(1);
// }


// async function runCrawler() {
//   const browser = await chromium.launch({ headless: true });
//   const page = await browser.newPage();

//   await page.goto('https://ransomwatch.telemetry.ltd/#/recentposts', {
//     waitUntil: 'domcontentloaded',
//   });

//   await page.waitForTimeout(5000);
//   const today = new Date().toISOString().slice(0, 10);

//   const groups = await page.evaluate((today) => {
//     const rows = Array.from(document.querySelectorAll('tbody tr'));
//     const matchingGroups = [];

//     for (const row of rows) {
//       const dateCell = row.querySelector('td');
//       const groupCell = row.querySelectorAll('td')[2];

//       if (dateCell && dateCell.textContent.trim() === today && groupCell) {
//         matchingGroups.push(groupCell.textContent.trim());
//       }
//     }

//     return [...new Set(matchingGroups)];
//   }, today);

//   await browser.close();

//   if (groups.length === 0) {
//     console.log(`[${today}] 기준 그룹이 없습니다.`);
//     return;
//   }

//   console.log(`Groups listed on ${today}:`, groups);

//   const groupsWithFqdn = [];

//   for (const group of groups) {
//     console.log(`\n--- ${group} ---`);
//     const fqdn = await getLatestOnionFQDN(group);

//     if (!fqdn) {
//       console.log(`❌ ${group}: 사용할 수 있는 .onion 주소가 없습니다.`);
//       continue;
//     }

//     console.log(`🧅 ${group} 최신 FQDN: ${fqdn}`);
//     groupsWithFqdn.push({ group, fqdn });
//   }

//   const outputPath = '/app/downloads/onion_list.json';
//   fs.writeFileSync(outputPath, JSON.stringify(groupsWithFqdn, null, 2));
//   console.log(`📦 저장 완료: ${outputPath}`);
// }

// async function getLatestOnionFQDN(groupName) {
//   try {
//     const res = await axios.get('https://ransomwhat.telemetry.ltd/groups');
//     const parsed = res.data;
//     const target = parsed.find(g => g.name === groupName);
//     if (!target || !target.locations) return null;

//     const sorted = target.locations
//       .filter(loc => loc.fqdn.endsWith('.onion') && loc.enabled)
//       .sort((a, b) => new Date(b.updated) - new Date(a.updated));

//     return sorted[0]?.fqdn || null;
//   } catch (err) {
//     console.error(`[ERROR] ${groupName} FQDN 요청 실패:`, err.message);
//     return null;
//   }
// }
const { chromium } = require('playwright');
const axios = require('axios');
const fs = require('fs');

// ✅ 안전한 page.goto() (retry 추가)
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
  console.log(`[▶️] Playwright 시작`);

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });  // docker에서는 --no-sandbox 추천
  const page = await browser.newPage();

  await safeGoto(page, 'https://ransomwatch.telemetry.ltd/#/recentposts', {
    waitUntil: 'domcontentloaded',
    timeout: 30000,   // 최대 30초 대기
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

// 🌀 최종 실행 부분
async function main() {
  console.log(`[▶️] Playwright 크롤러 시작`);
  await runCrawler();
}

main();
