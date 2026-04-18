/**
 * Siddim's Chest - Final Content Script
 * (Visual XAI Tooltip & Robust Matching)
 */

function renderHighlights(data) {
    console.log("하이라이트 렌더링 시작...", data);
    if (!data || !Array.isArray(data)) return;

    const coreItems = data.filter(item => item.is_core === true);
    if (coreItems.length === 0) return;

    // 툴팁 스타일 주입 (한 번만 실행)
    if (!document.getElementById('arona-style')) {
        const style = document.createElement('style');
        style.id = 'arona-style';
        style.innerHTML = `
            .arona-highlight-container {
                position: relative;
                display: inline;
                cursor: help;
            }
            .arona-mark {
                background-color: #ffd400 !important;
                color: #000 !important;
                font-weight: bold;
                border-radius: 2px;
                padding: 1px 0;
            }
            /* 나무위키 스타일 툴팁 */
            .arona-tooltip {
                visibility: hidden;
                width: 220px;
                background-color: #333;
                color: #fff;
                text-align: center;
                border-radius: 6px;
                padding: 10px;
                position: absolute;
                z-index: 99999;
                bottom: 150%; 
                left: 50%;
                margin-left: -110px;
                opacity: 0;
                transition: opacity 0.2s, transform 0.2s;
                transform: translateY(10px);
                font-size: 13px;
                font-weight: normal;
                line-height: 1.4;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.3);
                pointer-events: none;
                white-space: normal;
            }
            .arona-tooltip::after {
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            }
            .arona-highlight-container:hover .arona-tooltip {
                visibility: visible;
                opacity: 1;
                transform: translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    const contentArea = document.querySelector('article') || 
                        document.querySelector('.post-content') || 
                        document.querySelector('#articleBody') || 
                        document.body;

    coreItems.forEach((item, index) => {
        const cleanTarget = item.text.replace(/[|【】·]/g, ' ').replace(/\s+/g, ' ').trim();
        if (cleanTarget.length < 5) return;
        applyForceHighlight(contentArea, cleanTarget, item.reason);
    });
}

function applyForceHighlight(container, targetText, reason) {
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    let node;

    const words = targetText.split(/\s+/).filter(w => w.length > 0);
    const regexSource = words
        .map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
        .join('\\s*'); 
    
    try {
        const regex = new RegExp(`(${regexSource})`, 'g');

        while (node = walker.nextNode()) {
            const parent = node.parentNode;
            if (['MARK', 'SCRIPT', 'STYLE', 'TEXTAREA', 'SPAN'].includes(parent.tagName)) {
                if (parent.classList.contains('arona-highlight-container')) continue;
            }

            if (regex.test(node.textContent)) {
                const fragment = document.createDocumentFragment();
                const tempDiv = document.createElement('div');
                
                // [핵심] 마크와 툴팁을 하나로 묶는 구조로 치환
                const highlightedHTML = node.textContent.replace(regex, (match) => {
                    return `
                        <span class="arona-highlight-container">
                            <mark class="arona-mark">${match}</mark>
                            <span class="arona-tooltip">
                                <b style="color: #ffd400;">🎯 AI 판단 근거</b><br>${reason}
                            </span>
                        </span>`;
                });

                tempDiv.innerHTML = highlightedHTML;
                while (tempDiv.firstChild) {
                    fragment.appendChild(tempDiv.firstChild);
                }
                
                parent.insertBefore(fragment, node);
                parent.removeChild(node);
            }
        }
    } catch (e) {
        console.error("하이라이트 적용 중 에러:", e);
    }
}

// 메시지 리스너 유지
const api = typeof browser !== "undefined" ? browser : chrome;
api.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "highlight") {
        renderHighlights(request.data);
        sendResponse({status: "success"});
    }
    return true;
});