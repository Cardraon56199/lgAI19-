document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const statusDiv = document.getElementById('status');

    analyzeBtn.addEventListener('click', async () => {
        const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
        
        statusDiv.textContent = "분석 중... (Grok-4 가동 중)";
        analyzeBtn.disabled = true;

        try {
            // 1. 백엔드 통신
            const response = await fetch('http://localhost:8000/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: tab.url,
                    mode: document.getElementById('modeSelect').value,
                    keyword: document.getElementById('keywordInput').value
                })
            });

            const result = await response.json();

            if (result.status === "success") {
                // 2. 메시징 대신 '직접 실행' 방식 사용
                // 결과 데이터를 content.js에 주입하면서 함수 실행
                await browser.scripting.executeScript({
                    target: { tabId: tab.id },
                    func: (highlightData) => {
                        // 만약 content.js가 로드되어 있다면 그 안의 함수를 실행
                        if (typeof renderHighlights === "function") {
                            renderHighlights(highlightData);
                        } else {
                            console.error("Siddim's Chest: renderHighlights 함수를 찾을 수 없습니다. content.js가 로드되었는지 확인하세요.");
                        }
                    },
                    args: [result.data] // 백엔드 결과 데이터를 인자로 전달
                });
                
                statusDiv.textContent = "분석 완료!";
            }
        } catch (error) {
            console.error("최종 에러:", error);
            statusDiv.textContent = "에러: " + error.message;
        } finally {
            analyzeBtn.disabled = false;
        }
    });
});
