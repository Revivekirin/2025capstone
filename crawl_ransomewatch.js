const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://ransomwatch.telemetry.ltd/#/recentposts', {
    waitUntil: 'domcontentloaded',
  });

  await page.waitForTimeout(5000); 

  //const today = '2025-03-29';
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

    return matchingGroups;
  }, today);

  const uniqueGroups = [...new Set(groups)];
  console.log(`Groups listed on ${today}:`);
  console.log(uniqueGroups);

  await browser.close();
})();
