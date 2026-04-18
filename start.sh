#!/bin/bash

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Rapid Reading System Environment Checker ===${NC}"

# 1. 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${RED}[!] 가상환경(venv)이 활성화되어 있지 않습니다.${NC}"
    echo "명령어: source venv/bin/activate"
    exit 1
else
    echo -e "${GREEN}[V] 가상환경 활성화 확인: $VIRTUAL_ENV${NC}"
fi

# 2. 필수 라이브러리 체크
echo "--- 필수 라이브러리 체크 중 ---"
REQUIRED_PKGS=("fastapi" "uvicorn" "torch" "transformers" "trafilatura")
for pkg in "${REQUIRED_PKGS[@]}"; do
    if python -c "import $pkg" &> /dev/null; then
        echo -e "${GREEN}[V] $pkg 설치됨${NC}"
    else
        echo -e "${RED}[X] $pkg 누락됨 (pip install -r requirements.txt 필요)${NC}"
    fi
done

# 3. 모델 파일 체크
MODEL_DIR="./final_model"
if [ -d "$MODEL_DIR" ]; then
    echo -e "${GREEN}[V] 파인튜닝 모델 폴더 발견 ($MODEL_DIR)${NC}"
else
    echo -e "${RED}[X] 모델 폴더를 찾을 수 없습니다. 경로를 확인하세요.${NC}"
fi

# 4. 하드웨어 가속 가능성 체크 (Iris Xe용)
echo "--- 하드웨어 가속 분석 ---"
python -c "
import torch
print(f'- PyTorch 버전: {torch.__version__}')
print(f'- 사용 가능한 스레드 수: {torch.get_num_threads()}')
if torch.cuda.is_available():
    print('- CUDA 사용 가능 (NVIDIA GPU 감지)')
else:
    print('- CPU 기반 추론 모드 (Iris Xe 최적화 가능)')
"

# 5. 서버 실행 제안
echo -e "${GREEN}-------------------------------------------${NC}"
read -p "백엔드 서버(FastAPI)를 실행할까요? (y/n) " choice
if [ "$choice" == "y" ]; then
    echo "서버 실행 중... (0.0.0.0:8000)"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "검증 완료. 프로그램을 종료합니다."
fi
