from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
from openai import OpenAI
import json
import os

app = FastAPI()

# 1. CORS 설정: 브라우저 확장 프로그램 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Groq API 설정 (환경 변수 사용 권장)
# 터미널에서 export GROQ_API_KEY="본인키"를 입력하거나 .env 파일을 사용하세요.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "여기에 구글 chat에 올라온 api키를 적어주면 됩니다")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

class URLRequest(BaseModel):
    url: str

async def filter_core_sentences(sentences):
    """
    Groq LPU를 사용하여 문장 인덱스를 추출합니다.
    """
    if not sentences:
        return []

    # 프롬프트 최적화 (AI가 더 정확하게 숫자를 뽑도록 수정)
    prompt = f"""
    당신은 뉴스 기사 분석 전문가입니다. 아래 문장 목록에서 기사의 핵심 내용을 담은 문장의 '인덱스 번호'만 선택하세요.
    
    [규칙]
    1. 결과는 반드시 JSON 형식으로만 출력하세요: {{"core_ids": [번호, 번호]}}
    2. 가장 중요한 문장을 3~5개 사이로 골라주세요.
    3. 다른 설명은 절대로 하지 마세요.

    문장 목록:
    """
    for i, s in enumerate(sentences):
        prompt += f"\n[{i}] {s}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "당신은 뉴스 기사를 분석하여 핵심 문장 인덱스를 JSON으로 반환하는 봇입니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        raw_content = response.choices[0].message.content
        print(f"--- [DEBUG] Groq 응답: {raw_content} ---", flush=True)
        
        result = json.loads(raw_content)
        # AI가 보낸 값이 숫자가 아닐 경우를 대비해 정수형 변환 처리
        return [int(x) for x in result.get("core_ids", []) if str(x).isdigit()]
    except Exception as e:
        print(f"--- [ERROR] AI 분석 실패: {e} ---", flush=True)
        return []

@app.post("/analyze")
async def analyze_text(request: URLRequest):
    print(f"\n[작업 시작] URL: {request.url}", flush=True)
    
    try:
        # 1. 본문 데이터 추출
        downloaded = trafilatura.fetch_url(request.url)
        text = trafilatura.extract(downloaded)
        
        if not text:
            return {"data": [], "status": "no_content", "message": "본문을 읽어올 수 없습니다."}

        # 2. 문장 전처리 (너무 짧은 광고성 문장 제외)
        sentences = [s.strip() for s in text.split('\n') if s and len(s.strip()) > 15]
        print(f"📊 분석 대상: {len(sentences)}개 문장", flush=True)

        # 3. AI 분석 요청
        core_indices = await filter_core_sentences(sentences)
        
        # 4. 최종 데이터 구조 생성
        indexed_data = [
            {
                "id": i, 
                "text": s, 
                "is_core": i in core_indices
            } for i, s in enumerate(sentences)
        ]
        
        return {"data": indexed_data, "status": "success"}

    except Exception as e:
        print(f"❌ 서버 에러: {str(e)}", flush=True)
        return {"data": [], "error": str(e), "status": "error"}

if __name__ == "__main__":
    import uvicorn
    # 아치 리눅스에서 도커로 돌릴 때 8000 포트 개방
    uvicorn.run(app, host="0.0.0.0", port=8000)
