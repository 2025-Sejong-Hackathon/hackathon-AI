FROM python:3.11-slim

WORKDIR /app

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY code/ ./code/
COPY model/ ./model/
COPY data/ ./data/

# 포트 노출
EXPOSE 8002

# PYTHONPATH 설정 및 FastAPI 서버 실행
ENV PYTHONPATH=/app
CMD ["uvicorn", "code.main:app", "--host", "0.0.0.0", "--port", "8002"]
