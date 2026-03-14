import os
from openai import OpenAI  # <--- 이게 빠져서 에러가 났던 거예요!

# .env 파일이 있으면 직접 읽어서 환경 변수로 등록 (python-dotenv가 없을 때를 대비한 수동 로직)
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "GROQ_API_KEY" in line:
                key = line.split("=")[1].strip()
                os.environ["GROQ_API_KEY"] = key

# 키 로드 확인
raw_key = os.getenv("GROQ_API_KEY", "")

if not raw_key:
    print("❌ [에러] GROQ_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요!")
else:
    # 앞 7자리 출력해서 확인 (보안을 위해 7자리만)
    print(f"🔑 DEBUG: 현재 로드된 API KEY 앞부분 -> {raw_key[:7]}...")

    # 클라이언트 설정
    client = OpenAI(
        api_key=raw_key,
        base_url="https://api.groq.com/openai/v1",
    )

    try:
        # 간단한 테스트 호출
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": "안녕? 너는 누구야?"}],
            model="llama-3.3-70b-versatile",
        )
        print("✅ 연결 성공! 응답:", chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ 연결 실패 에러 내용: {e}")
