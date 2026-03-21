from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
from openai import OpenAI
import json
import os
import psutil
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

app = FastAPI()
server_logs = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 키 설정 (환경변수 권장, 모델명은 최신 grok-2-latest 사용)
XAI_API_KEY = os.getenv("XAI_API_KEY", "xai")
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


security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "lgai19team"
    correct_password = "lglgai1919"
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# 2. 시스템 로그를 담을 전역 리스트 (간단한 인메모리 로그)

def add_log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    server_logs.append(formatted_msg)
    if len(server_logs) > 50:
        server_logs.pop(0)
    print(formatted_msg, flush=True)

@app.websocket("/ws/log")
async def websocket_endpoint(websocket: WebSocket):
    global server_logs
    # 1. 연결 수락 (여기에 아까 그 비번 로직을 넣을 수도 있지만 일단 연결부터!)
    await websocket.accept()
    print:("📡 관제 센터에 새로운 기기가 연결되었습니다.")
    
    try:
        while True:
            # 2. 시스템 자원 수집 (0.5초마다 갱신)
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = int(f.read()) / 1000
            except: temp = "N/A"

            # 3. 데이터 패키징
            data = {
                "cpu": f"{cpu}%",
                "mem": f"{mem}%",
                "temp": f"{temp}°C",
                "logs": server_logs[::-1]  # 최신 로그가 위로
            }

            # 4. 클라이언트로 전송 (JSON 형식)
            await websocket.send_json(data)
            
            # 5. 너무 빨리 보내면 파이가 힘들어하니 0.5초 쉽니다.
            await asyncio.sleep(0.5) 
            
    except WebSocketDisconnect:
        add_log("🔌 관제 센터 연결이 종료되었습니다.")

from fastapi.responses import HTMLResponse

# 1. /log 경로로 접속하면 index.html 내용을 쏴줍니다.
@app.get("/log", response_class=HTMLResponse)
async def get_monitoring_page(username: str = Depends(authenticate)):
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>LG AI Team 19 - Realtime Monitor</title>
            <style>
                body { background: #0f0f0f; color: #00ff41; font-family: 'Courier New', monospace; padding: 20px; }
                .status-card { border: 1px solid #00ff41; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: inline-block; min-width: 250px; }
                .log-container { background: #1a1a1a; padding: 10px; border-radius: 5px; height: 350px; overflow-y: auto; border: 1px solid #333; }
                .metric { font-size: 1.2em; margin: 5px 0; }
                .temp-hot { color: #ff4141; }
            </style>
        </head>
        <body>
            <h1></h1>
            <div class="status-card">
                <div class="metric">🔥 CPU Temp: <span id="temp">--</span></div>
                <div class="metric">🤖 CPU Usage: <span id="cpu">--</span></div>
                <div class="metric">💾 RAM Usage: <span id="mem">--</span></div>
            </div>
            <h3>📜 Recent Logs (Real-time)</h3>
            <div id="logs" class="log-container"></div>

            <script>
                // 현재 접속 주소에 맞춰 자동으로 주소 설정 (이게 제일 안전함)
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = protocol + '//' + window.location.host + '/ws/log';
                const ws = new WebSocket(wsUrl);

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    document.getElementById('cpu').innerText = data.cpu;
                    document.getElementById('mem').innerText = data.mem;
                    const tempEl = document.getElementById('temp');
                    tempEl.innerText = data.temp;

                    if (parseFloat(data.temp) > 70) tempEl.className = 'temp-hot';
                    else tempEl.className = '';

                    // 로그창 업데이트 로직 수정
                    const logContainer = document.getElementById('logs');
                    if (data.logs) {
                        logContainer.innerHTML = data.logs.map(log => `<div>${log}</div>`).join('');
                    }
                };

                ws.onclose = function() {
                    console.log("🔌 연결이 끊겼습니다. 새로고침 하세요!");
                    document.getElementById('logs').innerHTML += '<div style="color: red;">[SYSTEM] 연결이 끊겼습니다.</div>';
                };
            </script>
        </body>
    </html>
    """
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
