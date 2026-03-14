/**
 * Siddim's Chest - Content Script
 * 역할을 수행하기 위해 전역 함수로 선언합니다.
 */

function renderHighlights(data) {
    console.log("[Siddim's Chest] 하이라이트 렌더링 시작...", data);

    if (!data || !Array.isArray(data)) {
        console.error("데이터 형식이 올바르지 않습니다.");
        return;
    }

    // 1. 핵심 문장만 필터링
    const coreSentences = data
        .filter(item => item.is_core === true)
        .map(item => item.text.trim());

    if (coreSentences.length === 0) {
        console.warn("하이라이트할 핵심 문장이 없습니다.");
        return;
    }

    // 2. 티스토리 본문 영역 우선 탐색 (범위를 좁혀야 정확도가 높음)
    const contentArea = document.querySelector('.entry-content') || 
                        document.querySelector('.tt_article_useless_p_margin') || 
                        document.querySelector('article') || 
                        document.body;

    console.log("탐색 영역:", contentArea);

    // 3. 각 문장별로 하이라이트 적용
    coreSentences.forEach((sentence, index) => {
        try {
            applyHighlightToContainer(contentArea, sentence);
            console.log(`[${index + 1}] 하이라이트 적용 시도: ${sentence.substring(0, 20)}...`);
        } catch (e) {
            console.error("하이라이트 적용 중 에러:", e);
        }
    });
}

/**
 * 특정 컨테이너 내의 텍스트를 찾아 <mark> 태그로 감쌉니다.
 */
function applyHighlightToContainer(container, targetText) {
    if (!targetText || targetText.length < 10) return;

    // 텍스트 노드만 순회하는 TreeWalker 생성
    const walker = document.createTreeWalker(
        container,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );

    let node;
    const nodesToProcess = [];

    // 1단계: 대상 문장을 포함하는 텍스트 노드 수집
    while (node = walker.nextNode()) {
        // 공백 차이로 인한 매칭 실패 방지를 위해 trim 및 normalize 처리
        if (node.textContent.replace(/\s+/g, ' ').includes(targetText.replace(/\s+/g, ' '))) {
            nodesToProcess.push(node);
        }
    }

    // 2단계: 수집된 노드 변경 (순회 중 변경하면 꼬이므로 분리 실행)
    nodesToProcess.forEach(textNode => {
        const parent = textNode.parentNode;
        
        // 이미 하이라이트 처리된 노드이거나 스크립트 태그면 패스
        if (parent.tagName === 'MARK' || parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE') return;

        const originalText = textNode.textContent;
        const safeTarget = targetText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // 정규표현식 특수문자 이스케이프
        const regex = new RegExp(`(${safeTarget.replace(/\s+/g, '\\s+')})`, 'g');

        // HTML 삽입을 위해 임시 요소 생성
        const span = document.createElement('span');
        span.innerHTML = originalText.replace(regex, '<mark style="background-color: #fff5b1; color: #000; font-weight: bold; border-radius: 2px;">$1</mark>');
        
        // 조각난 노드들을 기존 위치에 삽입
        while (span.firstChild) {
            parent.insertBefore(span.firstChild, textNode);
        }
        parent.removeChild(textNode);
    });
}

// 메시지 리스너 (혹시 모를 메시지 방식 대응용)
if (typeof browser !== "undefined") {
    browser.runtime.onMessage.addListener((message) => {
        if (message.action === "highlight") {
            renderHighlights(message.data);
        }
    });
}
