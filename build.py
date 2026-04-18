import os
import sys
import subprocess
import shutil
from cryptography.fernet import Fernet

# --- [설정] ---
APP_NAME = "RapidReader_Encrypted"
MAIN_SCRIPT = "server.py"
MODEL_DIR = "final_model"
ENC_MODEL_DIR = "encrypted_model" # 암호화된 파일이 저장될 임시 폴더
SECRET_KEY_FILE = "secret.key" # 암호화 키 파일

def generate_key():
    if not os.path.exists(SECRET_KEY_FILE):
        key = Fernet.generate_key()
        with open(SECRET_KEY_FILE, "wb") as f:
            f.write(key)
        print(f"[*] 새 암호화 키 생성 완료: {SECRET_KEY_FILE}")
    return open(SECRET_KEY_FILE, "rb").read()

def encrypt_models():
    key = generate_key()
    fernet = Fernet(key)
    
    if os.path.exists(ENC_MODEL_DIR):
        shutil.rmtree(ENC_MODEL_DIR)
    os.makedirs(ENC_MODEL_DIR)

    print(f"[*] {MODEL_DIR} 내부 파일 암호화 중...")
    for filename in os.listdir(MODEL_DIR):
        file_path = os.path.join(MODEL_DIR, filename)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            encrypted_data = fernet.encrypt(data)
            with open(os.path.join(ENC_MODEL_DIR, filename + ".enc"), "wb") as f:
                f.write(encrypted_data)
    print("[*] 모든 모델 파일 암호화 완료.")

def build():
    encrypt_models()
    
    separator = ";" if os.name == "nt" else ":"
    build_cmd = [
        "pyinstaller", "--onefile", "--noconsole", "--clean",
        f"--name={APP_NAME}",
        # 암호화된 폴더와 키 파일을 EXE 안에 포함
        f"--add-data={ENC_MODEL_DIR}{separator}{ENC_MODEL_DIR}",
        f"--add-data={SECRET_KEY_FILE}{separator}.",
        MAIN_SCRIPT
    ]
    
    print("[*] PyInstaller 빌드 시작...")
    subprocess.check_call(build_cmd)
    print(f"✅ 빌드 완료: dist/{APP_NAME}")

if __name__ == "__main__":
    build()