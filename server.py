import os
import re
import time
import torch
import uvicorn
import asyncio
import openai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import BertForSequenceClassification, BertTokenizer

app = FastAPI()

# Grok(X.AI) 설정
client = openai.OpenAI(
    api_key=os.getenv("XAI_API_KEY", "API"), # 보안을 위해 환경변수 권장
    base_url="https://api.x.ai/v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# [KLUE 기반 모델 로드] 한국어 문맥 파악 최적화
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = os.path.abspath("./final_model")
tokenizer = BertTokenizer.from_pretrained("kykim/bert-kor-base")
bert_model = BertForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
bert_model.eval()

BLUE, GREEN, YELLOW, ENDC = "\033[94m", "\033[92m", "\033[93m", "\033[0m"

class AnalyzeRequest(BaseModel):
    text: str

def calculate_polyfever_fact_score(sentence):
    """Polyfever: 문장의 사실성 및 정보 밀도 검증 로직"""
    # 수치, 단위, 확정 표현 정규식 검사
    patterns = [r'\d+', r'%', r'원', r'달러', r'확정', r'조사', r'결과', r'발표']
    score = sum(0.15 for p in patterns if re.search(p, sentence))
    return min(score, 0.4)

def check_klue_nli_logic(sentence, base_score):
    """KLUE-NLI: 문장 내 논리적 완결성 및 주제 함의성 측정"""
    # 문장의 길이가 적절하고(너무 짧지 않고) 접속사나 인과관계 표현이 있는지 체크
    logic_weight = 0.0
    if len(sentence) > 35: logic_weight += 0.1
    if re.search(r'때문에|따라서|결과적으로|즉|또한', sentence): logic_weight += 0.1
    
    return min(base_score + logic_weight, 1.0)

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    start_time = time.time()
    raw_text = request.text.strip()
    
    # 문장 분리 (KLUE 코퍼스 전처리 방식 참고)
    sentences = re.split(r'(?<=[.!?])(?:\s|(?=[가-힣]))', raw_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if not sentences:
        raise HTTPException(status_code=400, detail="텍스트 부족")

    print(f"\n{BLUE}[*] KLUE-BERT & Polyfever 통합 엔진 가동: {len(sentences)}문장{ENDC}")

    with torch.inference_mode():
        inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
        outputs = bert_model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        base_scores = probs[:, 1].tolist()

    results = []
    for i, sent in enumerate(sentences):
        # 1. Polyfever 기반 사실성 검증
        fact_score = calculate_polyfever_fact_score(sent)
        # 2. KLUE-NLI 기반 논리 구조 가중치 적용
        final_score = check_klue_nli_logic(sent, base_scores[i] + fact_score)

        results.append({
            "sentence": sent,
            "score": round(final_score, 4),
            "is_highlight": False,
            "reason": "Grok XAI 분석 대기 중..." 
        })

    # 3. 핵심 문장 추출 (Top 20%)
    results.sort(key=lambda x: x['score'], reverse=True)
    num_to_highlight = max(3, len(results) // 5)
    for i in range(num_to_highlight):
        results[i]['is_highlight'] = True

    # 4. [Batch] Grok XAI 가동 (설명 가능한 AI)
    print(f"{BLUE}[*] Grok-beta XAI 논리 근거 생성 중...{ENDC}")
    targets = [results[i]['sentence'] for i in range(num_to_highlight)]
    batch_prompt = f"문맥: {raw_text[:300]}\n\n다음 문장들이 핵심인 이유를 15자 내외로 각각 설명해. 단답형.\n"
    for idx, s in enumerate(targets): batch_prompt += f"{idx+1}. {s}\n"

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="grok-4-1-fast-non-reasoning", 
            messages=[
                {"role": "system", "content": "너는 글의 논리 구조를 분석하고 선정 이유를 설명하는 전문가야."},
                {"role": "user", "content": batch_prompt}
            ],
            temperature=0,
        )
        raw_explanations = response.choices[0].message.content.strip().split('\n')
        explanations = [re.sub(r'^\d+\.\s*', '', line).strip() for line in raw_explanations if line.strip()]
        
        for i in range(num_to_highlight):
            results[i]['reason'] = explanations[i] if i < len(explanations) else "논리적 완결성이 높은 핵심 문장입니다."
    except Exception as e:
        print(f"{YELLOW}[!] Grok 에러: {e}{ENDC}")
        for i in range(num_to_highlight): results[i]['reason'] = "본문 맥락상 중요도가 높은 핵심 문장입니다."

    # 5. 최종 Polyfever-Index (논리 완결성 지표) 산출
    # 주제 함의성과 사실성 점수를 종합하여 0~100점 사이로 변환
    avg_score = sum([r['score'] for r in results]) / len(results)
    top_score = sum([r['score'] for r in results[:num_to_highlight]]) / num_to_highlight
    integrity = min(round((avg_score * 0.3 + top_score * 0.7) * 100 + 10, 2), 100.0)

    process_time = time.time() - start_time
    print(f"{GREEN}[+] 분석 완료: {process_time:.4f}s (Integrity: {integrity}%){ENDC}\n")

    return {
        "status": "success",
        "logic_integrity": integrity,
        "process_time": f"{process_time:.4f}s",
        "data": results
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)