/**
 * Team 19: Rapid Reading System
 * Final Sidebar Controller (KLUE & Polyfever UX Optimized)
 */

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyze-btn');
    const statusText = document.getElementById('engine-text');
    const statusDot = document.getElementById('engine-status');
    
    const logicScoreEl = document.getElementById('logic-score');
    const logicGaugeEl = document.getElementById('logic-gauge');
    const processTimeEl = document.getElementById('process-time');
    const highlightList = document.getElementById('highlight-list');

    analyzeBtn.addEventListener('click', async () => {
        const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
        
        analyzeBtn.disabled = true;
        if (statusText) statusText.textContent = "본문 데이터 추출 및 정규화...";
        if (statusDot) statusDot.style.backgroundColor = "#ffc107"; 

        try {
            // 본문 텍스트 추출
            const [{ result: pageText }] = await browser.scripting.executeScript({
                target: { tabId: tab.id },
                func: () => document.body.innerText
            });

            if (!pageText || pageText.length < 20) {
                throw new Error("분석할 텍스트가 너무 적습니다.");
            }

            if (statusText) statusText.textContent = "엔진 분석 중 (KLUE-NLI + Polyfever)...";

            // 서버 통신
            const response = await fetch('http://127.0.0.1:8000/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: pageText })
            });

            if (!response.ok) throw new Error("서버 응답 오류 (server.py 구동 확인 요망)");

            const resData = await response.json();

            if (resData.status === "success") {
                // 1. [UX] 논리 완결성 지표 업데이트 (소수점 2자리로 정밀도 강조)
                const integrity = parseFloat(resData.logic_integrity).toFixed(2);
                if (logicScoreEl) logicScoreEl.textContent = integrity;
                
                if (logicGaugeEl) {
                    logicGaugeEl.style.width = `${integrity}%`;
                    // 점수에 따른 다이내믹 컬러 (Polyfever 지수 기반)
                    logicGaugeEl.style.backgroundColor = integrity > 80 ? "#28a745" : (integrity > 50 ? "#ffc107" : "#dc3545");
                }
                
                if (processTimeEl) processTimeEl.textContent = resData.process_time;

                // 2. 하단 리스트 업데이트 (XAI 이유 포함)
                updateHighlightList(resData.data, highlightList);

                // 3. 본문 하이라이트 주입
                const mappedData = resData.data.map(item => ({
                    text: item.sentence,
                    is_core: item.is_highlight,
                    reason: item.reason 
                }));

                await browser.scripting.executeScript({
                    target: { tabId: tab.id },
                    func: (coreData) => {
                        if (typeof renderHighlights === "function") {
                            renderHighlights(coreData);
                        } else {
                            console.error("본문 하이라이트 엔진(content.js) 로드 실패");
                        }
                    },
                    args: [mappedData]
                });

                if (statusText) statusText.textContent = "분석 및 검증 완료!";
                if (statusDot) statusDot.style.backgroundColor = "#28a745";
            }
        } catch (error) {
            console.error("Sidebar Error:", error);
            if (statusText) statusText.textContent = "에러: " + error.message;
            if (statusDot) statusDot.style.backgroundColor = "#dc3545";
        } finally {
            analyzeBtn.disabled = false;
        }
    });
});

// [UI] 하이라이트 리스트 및 나무위키 스타일 버튼 생성
function updateHighlightList(data, listElement) {
    if (!listElement) return;
    listElement.innerHTML = "";
    
    const highlights = data.filter(item => item.is_highlight);
    
    if (highlights.length === 0) {
        listElement.innerHTML = '<li class="empty-msg">핵심 문장을 식별하지 못했습니다.</li>';
        return;
    }

    highlights.slice(0, 5).forEach((item) => {
        const li = document.createElement('li');
        li.className = 'highlight-item';
        li.style.cssText = "margin-bottom: 12px; padding: 10px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #0275d8;";

        li.innerHTML = `
            <div style="font-size: 0.9em; line-height: 1.5; color: #333;">
                "${item.sentence.substring(0, 55)}..."
                <span class="wiki-btn" 
                      style="color: #0275d8; font-size: 0.8em; cursor: pointer; font-weight: bold; vertical-align: super; margin-left: 2px;"
                      data-reason="${item.reason}">[이유]</span>
            </div>
        `;

        li.querySelector('.wiki-btn').addEventListener('click', (e) => {
            // 버튼 근처에 팝업 띄우기
            showReasonPopup(e.clientX, e.clientY, e.target.getAttribute('data-reason'));
        });

        listElement.appendChild(li);
    });
}

// [UX] XAI 근거 팝업
function showReasonPopup(x, y, text) {
    let popup = document.getElementById('xai-popup');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'xai-popup';
        popup.style.cssText = `
            position: fixed; z-index: 10000; background: #ffffff; border: 1.5px solid #0275d8;
            padding: 10px 14px; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            font-size: 0.85em; max-width: 220px; color: #333; pointer-events: none;
            transition: opacity 0.2s, transform 0.2s; transform: translateY(0);
        `;
        document.body.appendChild(popup);
    }
    
    popup.innerHTML = `<span style="color: #0275d8; font-weight: bold;">💡 AI 분석 근거 (XAI)</span><br>${text}`;
    popup.style.display = 'block';
    popup.style.opacity = '1';
    
    // 팝업 위치 (사이드바 내부 버튼 왼쪽으로 배치)
    popup.style.left = `${x - 240}px`; 
    popup.style.top = `${y - 15}px`;

    setTimeout(() => {
        popup.style.opacity = '0';
        setTimeout(() => { popup.style.display = 'none'; }, 200);
    }, 3500); // 3.5초간 노출
}