from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
from openai import OpenAI
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 키 설정 (환경변수 권장, 모델명은 최신 grok-2-latest 사용)
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

class URLRequest(BaseModel):
    url: str
    mode: str = "balanced"  # summary, balanced, detailed
    keyword: str = ""       # 사용자가 강조하고 싶은 단어

async def filter_core_sentences(sentences, mode, keyword):
    if not sentences:
        return []

    # 모드별 지침 세분화
    instructions = {
        "summary": "글 전체를 관통하는 가장 압도적으로 중요한 핵심 문장 3개만 엄격하게 골라내세요.",
        "balanced": "전체 맥락을 고려하되, 도입부와 결론을 포함하여 글 전체에 골고루 분포된 핵심 문장 5개를 고르세요.",
        "detailed": "각 문단별 논거가 포함된 문장을 찾아내세요. 중요도가 높다면 최대 8개까지 선정 가능합니다."
    }
    
    selected_instruction = instructions.get(mode, instructions["balanced"])
    keyword_instruction = f"\n5. 특히 '{keyword}'와(과) 관련된 내용이 있다면 우선적으로 고려하세요." if keyword else ""

    prompt = f"""
당신은 뉴스 분석 전문가입니다. 아래 지침에 따라 제공된 문장 목록에서 핵심 문장의 인덱스를 추출하세요.

[지침]
1. {selected_instruction}
2. 결과는 반드시 JSON 형식으로만 출력하세요: {{"core_ids": [인덱스번호, 인덱스번호]}}
3. 다른 설명이나 인사말은 절대로 하지 마세요.
4. 정보 밀도가 높고 그 자체로 완결성이 있는 문장을 고르세요.{keyword_instruction}

[문장 목록]
"""
    for i, s in enumerate(sentences):
        prompt += f"\n[{i}] {s}"

    try:
        response = client.chat.completions.create(
            model="grok-3-mini", # 모델명 확인 필요
            messages=[
                {"role": "system", "content": "핵심 문장 인덱스를 JSON으로 반환하는 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            stream=False
        )
        
        raw_content = response.choices[0].message.content
        result = json.loads(raw_content)
        return [int(x) for x in result.get("core_ids", []) if str(x).isdigit()]
    except Exception as e:
        print(f"--- [ERROR] AI 분석 실패: {e} ---")
        return []

@app.post("/analyze")
async def analyze_text(request: URLRequest):
    print(f"\n[작업 시작] URL: {request.url} | 모드: {request.mode}", flush=True)
    try:
        downloaded = trafilatura.fetch_url(request.url)
        text = trafilatura.extract(downloaded)
        
        if not text:
            print("[경고] 본문을 추출하지 못했습니다.", flush=True)
            return {"data": [], "status": "no_content"}

        sentences = [s.strip() for s in text.split('\n') if s and len(s.strip()) > 15]
        print(f"[정보] 추출된 전체 문장 개수: {len(sentences)}개", flush=True)
        
        core_indices = await filter_core_sentences(sentences, request.mode, request.keyword)
        print(f"[성공] AI가 선정한 핵심 문장 인덱스: {core_indices}", flush=True) # <-- 이거 추가!
        
        indexed_data = [
            {"id": i, "text": s, "is_core": i in core_indices} 
            for i, s in enumerate(sentences)
        ]
        
        # 핵심 문장만 필터링해서 로그에 한 번 더 찍어보기
        core_texts = [s for i, s in enumerate(sentences) if i in core_indices]
        for ct in core_texts:
            print(f" >> 핵심문장: {ct}", flush=True)

        return {"data": indexed_data, "status": "success"}
    except Exception as e:
        print(f"[에러] analyze_text 실패: {e}", flush=True)
        return {"data": [], "error": str(e), "status": "error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
