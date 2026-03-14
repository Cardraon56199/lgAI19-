from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
from openai import OpenAI
import json
import os

app = FastAPI()

#권한 요청
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#API키 설정, 코드에 있는 api키는 현재 만료되었음
client = OpenAI(
    api_key="",
    base_url="https://api.groq.com/openai/v1",
)

#URL받아오기
class URLRequest(BaseModel):
    url: str

#AI프롬포트 설정 및 데이터 보내는 함수
async def filter_core_sentences(sentences):
    """
    Groq LPU의 속도를 활용하여 문장 인덱스를 추출합니다.
    """
    if not sentences:
        return []

    # AI가 헷갈리지 않게 인덱스와 문장을 명확히 구분한 프롬프트
    prompt = f"""
    당신은 뉴스 기사의 핵심 논거를 추출하는 전문가입니다. 
    아래 문장 목록에서 기사의 주제를 가장 잘 뒷받침하는 '핵심 문장'의 인덱스 번호만 골라주세요.
    
    [조건]
    1. 반드시 JSON 형식으로 답하세요: {{"core_ids": [인덱스번호, 인덱스번호]}}
    2. 가장 중요한 문장을 최대 5개까지만 선택하세요.
    3. 설명 없이 JSON만 출력하세요.

    문장 목록:
    """
    for i, s in enumerate(sentences):
        prompt += f"\n[{i}] {s}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "당신은 JSON 데이터만 생성하는 유능한 분석 엔진입니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        raw_content = response.choices[0].message.content
        print(f"--- [DEBUG] Groq AI 응답: {raw_content} ---", flush=True)
        
        result = json.loads(raw_content)
        return result.get("core_ids", [])
    except Exception as e:
        print(f"--- [ERROR] AI 분석 중 오류 발생: {e} ---", flush=True)
        return []

#분석(trafilatura로 본문 분석하고 위에서 선언한 함수로 AI에게 요청)
@app.post("/analyze")
async def analyze_text(request: URLRequest):
    print(f"\n[작업 시작] URL: {request.url}", flush=True)
    
    try:
        # 1. 본문 데이터 추출
        downloaded = trafilatura.fetch_url(request.url)
        text = trafilatura.extract(downloaded)
        
        if not text:
            print("본문 내용 추출 실패", flush=True)
            return {"data": [], "status": "no_content"}

        # 2. 문장 전처리 (빈 줄 제거 및 최소 길이 필터링), 인덱스 값도 부여
        sentences = [s.strip() for s in text.split('\n') if s and len(s.strip()) > 10]
        print(f"📊 총 {len(sentences)}개 문장 확보", flush=True)

        # 3. AI 호출
        core_indices = await filter_core_sentences(sentences)
        print(f"선별된 문장: {core_indices}", flush=True)

        # 4. 프론트엔드용 데이터 구조 생성
        # AI가 선택한 인덱스에 해당하는 문장에만 is_core = True 부여
        indexed_data = [
            {
                "id": i, 
                "text": s, 
                "is_core": i in core_indices
            } for i, s in enumerate(sentences)
        ]
        
        return {"data": indexed_data, "status": "success"}

    except Exception as e:
        print(f"error: {str(e)}", flush=True)
        return {"data": [], "error": str(e), "status": "error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
