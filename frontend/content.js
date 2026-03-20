/**
 * Siddim's Chest - Ultra Robust Content Script
 */

function renderHighlights(data) {
    console.log("하이라이트 렌더링 시작...", data);

    if (!data || !Array.isArray(data)) {
        console.error("데이터가 배열 형식이 아닙니다.");
        return;
    }

    const coreSentences = data
        .filter(item => item.is_core === true)
        .map(item => item.text.trim());

    if (coreSentences.length === 0) {
        console.warn("핵심 문장이 없습니다.");
        return;
    }

    // 나무위키 AMP 및 다크모드 대응을 위한 타겟 영역 확장
    const contentArea = document.querySelector('article') || 
                        document.querySelector('.w') || 
                        document.querySelector('.theseed-dark-mode') || 
                        document.body;

    console.log("최종 탐색 영역:", contentArea);

    coreSentences.forEach((sentence, index) => {
        // 문장에서 매칭을 방해하는 특수문자들 제거
        const cleanTarget = sentence.replace(/[|【】·]/g, ' ').replace(/\s+/g, ' ').trim();
        if (cleanTarget.length < 5) return;

        console.log(`[${index + 1}] 매칭 시도: ${cleanTarget.substring(0, 30)}...`);
        applyForceHighlight(contentArea, cleanTarget);
    });
}

function applyForceHighlight(container, targetText) {
    // 텍스트 노드 순회
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    let node;

    // 공백 무시 정규식 생성
    const words = targetText.split(/\s+/).filter(w => w.length > 0);
    const regexSource = words
        .map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
        .join('\\s*'); // 단어 사이에 어떤 공백/줄바꿈이 있어도 허용
    
    try {
        const regex = new RegExp(`(${regexSource})`, 'g');

        while (node = walker.nextNode()) {
            const parent = node.parentNode;
            if (['MARK', 'SCRIPT', 'STYLE', 'TEXTAREA'].includes(parent.tagName)) continue;

            if (regex.test(node.textContent)) {
                console.log("🎯🎯 매칭 성공!");
                const span = document.createElement('span');
                // 나무위키 다크모드에서도 눈에 잘 띄는 색상
                span.innerHTML = node.textContent.replace(regex, 
                    '<mark style="background-color: #ffd400 !important; color: #000 !important; font-weight: bold; border-radius: 2px;">$1</mark>');
                
                parent.insertBefore(span, node);
                parent.removeChild(node);
            }
        }
    } catch (e) {
        console.error("정규식 생성 또는 적용 중 에러:", e);
    }
}

// 메시지 리스너 (확실하게 등록)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "highlight") {
        renderHighlights(request.data);
        sendResponse({status: "success"});
    }
});
