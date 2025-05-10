const axios = require('axios');
const fs = require('fs');

const URL = 'https://thehackernews.com/';

(async () => {
  try {
    const response = await axios.get(URL, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      },
      timeout: 15000,
    });

    const html = response.data;

    // 파일로 저장 (선택)
    fs.writeFileSync('thehackernews.html', html, 'utf-8');
    console.log('✅ HTML 저장 완료: thehackernews.html');
  } catch (error) {
    console.error('❌ 요청 실패:', error.message);
  }
})();
