browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.command === "highlight") {
    console.log("메시지 수신 완료, 하이라이트 시작", message.data);
    
    // 백엔드 응답 구조에 맞게 수정 (result.data 안에 리스트가 있음)
    const data = message.data.data;
    
    data.forEach(item => {
      // 핵심 문장(is_core: true)인 경우에만 하이라이트 실행
      if (!item.is_core) return;

      const sentence = item.text.trim();
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      let node;

      while (node = walk.nextNode()) {
        const nodeText = node.textContent.replace(/\s+/g, ' ');
        const targetText = sentence.replace(/\s+/g, ' ');

        // 이미 하이라이트 된 부모 노드라면 스킵
        if (node.parentNode.classList.contains('ai-highlighted')) continue;

        if (nodeText.includes(targetText) && targetText.length > 5) {
          console.log("🎯 하이라이트 매칭 성공:", targetText.substring(0, 15) + "...");
          
          const span = document.createElement('span');
          span.className = 'ai-highlighted'; // 중복 방지용 클래스
          span.style.backgroundColor = 'rgba(255, 255, 0, 0.5)'; // 반투명 노란색
          span.style.borderBottom = '2px solid orange';
          span.style.borderRadius = '3px';
          
          // 기존 텍스트 노드를 span으로 교체
          const parent = node.parentNode;
          if (parent) {
            span.textContent = node.textContent;
            parent.replaceChild(span, node);
          }
        }
      }
    });
  }
});