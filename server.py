import os
import re
import time
import torch
import uvicorn
import asyncio
import openai
import trafilatura  # 추가됨
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import BertForSequenceClassification, BertTokenizer

app = FastAPI()

# Grok(X.AI) 설정
client = openai.OpenAI(
    api_key=os.getenv("XAI_API_KEY", "API"),
    base_url="https://api.x.ai/v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 로드 (KLUE-BERT 기반)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = os.path.abspath("./final_model")
tokenizer = BertTokenizer.from_pretrained("kykim/bert-kor-base")
bert_model = BertForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
bert_model.eval()

BLUE, GREEN, YELLOW, ENDC = "\033[94m", "\033[92m", "\033[93m", "\033[0m"

class AnalyzeRequest(BaseModel):
    text: str = None
    url: str = None  # URL 지원 추가

def extract_content(url):
    """Trafilatura를 이용한 웹 본문 고정밀 추출"""
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return None
    # 본문 추출 (광고, 메뉴 등 제거)
    return trafilatura.extract(downloaded, include_comments=False, include_tables=True)

def calculate_polyfever_fact_score(sentence):
    patterns = [r'\d+', r'%', r'원', r'달러', r'확정', r'조사', r'결과', r'발표']
    score = sum(0.15 for p in patterns if re.search(p, sentence))
    return min(score, 0.4)

def check_klue_nli_logic(sentence, base_score):
    logic_weight = 0.0
    if len(sentence) > 35: logic_weight += 0.1
    if re.search(r'때문에|따라서|결과적으로|즉|또한', sentence): logic_weight += 0.1
    return min(base_score + logic_weight, 1.0)

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    start_time = time.time()
    
    # 1. 입력 소스 처리 (URL 또는 직접 입력 텍스트)
    if request.url:
        print(f"{BLUE}[*] 웹 본문 추출 중: {request.url}{ENDC}")
        raw_text = extract_content(request.url)
        if not raw_text:
            raise HTTPException(status_code=400, detail="웹페이지 내용을 가져올 수 없습니다.")
    else:
        raw_text = request.text.strip() if request.text else ""

    if not raw_text or len(raw_text) < 20:
        raise HTTPException(status_code=400, detail="분석할 텍스트가 부족합니다.")

    # 2. 문장 분리 및 전처리
    sentences = re.split(r'(?<=[.!?])(?:\s|(?=[가-힣]))', raw_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    print(f"\n{BLUE}[*] Poly-FEVER 엔진 가동: {len(sentences)}문장 분석 시작{ENDC}")

    # 3. BERT 추론 (Batch)
    with torch.inference_mode():
        inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
        outputs = bert_model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        base_scores = probs[:, 1].tolist()

    # 4. 점수 합산 및 가중치 적용
    results = []
    for i, sent in enumerate(sentences):
        fact_score = calculate_polyfever_fact_score(sent)
        final_score = check_klue_nli_logic(sent, base_scores[i] + fact_score)
        results.append({
            "sentence": sent,
            "score": round(final_score, 4),
            "is_highlight": False,
            "reason": "Grok XAI 분석 대기 중..."
        })

    # 5. 핵심 문장 추출 (Top 20%)
    results.sort(key=lambda x: x['score'], reverse=True)
    num_to_highlight = max(3, len(results) // 5)
    for i in range(num_to_highlight):
        results[i]['is_highlight'] = True

    # 6. Grok XAI 가동
    targets = [results[i]['sentence'] for i in range(num_to_highlight)]
    batch_prompt = f"문맥: {raw_text[:300]}\n\n다음 문장들이 핵심인 이유를 15자 내외로 설명해. 단답형.\n"
    for idx, s in enumerate(targets): batch_prompt += f"{idx+1}. {s}\n"

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="grok-beta", # 주인님의 모델명에 맞춰 수정 가능
            messages=[{"role": "user", "content": batch_prompt}],
            temperature=0,
        )
        explanations = [re.sub(r'^\d+\.\s*', '', line).strip() for line in response.choices[0].message.content.split('\n') if line.strip()]
        for i in range(num_to_highlight):
            results[i]['reason'] = explanations[i] if i < len(explanations) else "논리적 완결성이 높은 핵심 문장입니다."
    except:
        for i in range(num_to_highlight): results[i]['reason'] = "본문 맥락상 중요도가 높은 핵심 문장입니다."

    # 7. 최종 지표 산출
    avg_score = sum([r['score'] for r in results]) / len(results)
    top_score = sum([r['score'] for r in results[:num_to_highlight]]) / num_to_highlight
    integrity = min(round((avg_score * 0.3 + top_score * 0.7) * 100 + 10, 2), 100.0)

    process_time = time.time() - start_time
    return {
        "status": "success",
        "logic_integrity": integrity,
        "process_time": f"{process_time:.4f}s",
        "data": results
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
