# 베이스 이미지
FROM python:3.10-slim

# 환경 변수 설정 (필수 아님)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 시스템 패키지 설치 + Chrome 설치
RUN apt-get update && \
    apt-get install -y wget curl gnupg fonts-liberation libasound2 libnspr4 libnss3 libxss1 xdg-utils unzip && \
    curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# 작업 디렉토리 지정
WORKDIR /app

# 현재 프로젝트 전체 복사
COPY . /app

# 파이썬 패키지 설치
RUN pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput

# 포트 오픈 (Render는 8000 사용)
EXPOSE 8000

# Gunicorn으로 앱 실행
CMD ["gunicorn", "back.wsgi:application", "--bind", "0.0.0.0:8000"]
