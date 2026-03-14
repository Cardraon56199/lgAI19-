from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
import sys

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

@app.post("/analyze")
async def analyze_text(request: URLRequest):
    print(f"\n[입력 URL 확인]: {request.url}", flush=True) # flush로 즉시 출력
    
    downloaded = trafilatura.fetch_url(request.url)
    text = trafilatura.extract(downloaded)
    
    if not text:
        print("!!! 본문 추출 실패 !!!", flush=True)
        return {"data": []}

    sentences = [s.strip() for s in text.split('\n') if len(s.strip()) > 10]
    
    # 아치 터미널에 확실히 찍히도록 반복문 사용
    print(f"--- 추출된 문장 ({len(sentences)}개) ---", flush=True)
    for i, s in enumerate(sentences[:5]):
        print(f"DEBUG {i}: {s[:50]}...", flush=True)
    
    return {"data": [{"id": i, "text": s} for i, s in enumerate(sentences)]}
