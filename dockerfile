# Python 3.12 버전의 슬림 이미지 사용
FROM python:3.12-slim

# 작업 디렉토리 생성
WORKDIR /app

# 의존성 파일 복사
COPY requirements.txt .

# 시스템 패키지 설치 (예: libgl1)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ✅ Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY app ./app

# 포트 설정 (FastAPI 기본 포트는 8000)
EXPOSE 8000

# 컨테이너 시작 시 실행할 명령어
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
