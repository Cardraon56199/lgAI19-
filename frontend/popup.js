document.getElementById('analyzeBtn').addEventListener('click', async () => {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  const statusEl = document.getElementById('status');
  statusEl.innerText = '데이터 분석 중...';

  try {
    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: tab.url })
    });
    
    const result = await response.json();
    
    // [파폭 개발자 도구 콘솔 출력]
    console.log("--- 서버 응답 데이터 상세 ---");
    console.log("전체 데이터:", result);
    console.log("문장 개수:", result.data ? result.data.length : 0);
    
    // content.js로 데이터 전달
    await browser.tabs.sendMessage(tab.id, { command: "highlight", data: result });
    statusEl.innerText = '분석 및 하이라이트 완료!';
  } catch (error) {
    console.error("통신 에러:", error);
    statusEl.innerText = '에러 발생 (콘솔 확인)';
  }
});
