
# 이미지 기반이 될 베이스 이미지
FROM python:3

ENV PYTHONUNBUFFERED 1\
    DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}\
    DJANGO_DEBUG=${DJANGO_DEBUG}\
    DB_HOST=${DB_HOST}\
    DB_USER=${DB_USER}\
    DB_PASSWORD=${DB_PASSWORD}\
    DB_NAME=${DB_NAME}\
    FTP_USER=${FTP_USER}\
    FTP_PASSWORD=${FTP_PASSWORD}\
    WAS_HOST=${WAS_HOST}\
    CHATGPT_API_KEY=${CHATGPT_API_KEY}
#############################################################################################################################################################
# # EC2 에서는 리소스가 부족해서 실행하기가 어려워서 주석 처리
# # dcinside에서 이미지 다운로드가 어려운 점 때문에 이용했기 때문에 다른 커뮤니티는 Chromedriver가 필요가 없음.
# # Chromedriver 다운로드 및 설치
# RUN apt-get update && apt-get install -y \
#     wget \
#     unzip \
#     gnupg \
#     && rm -rf /var/lib/apt/lists/*

# # Chrome 브라우저 설치
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
#     && apt-get update \
#     && apt-get install -y google-chrome-stable

# # Chromedriver 설치
# # https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.86/linux64/chrome-linux64.zip 
# # https://chromedriver.storage.googleapis.com/123.0.6312.86/chromedriver_linux64.zip
# RUN wget -q -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.86/linux64/chromedriver-linux64.zip \
#     && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
#     && rm /tmp/chromedriver.zip
# RUN chmod +x /usr/local/bin/chromedriver
#############################################################################################################################################################

# Img To Text
RUN apt-get update && apt-get install -y \
    tesseract-ocr

# 작업디렉토리 설정
WORKDIR /web

# logs 
RUN mkdir logs

# 소스코드 복사
COPY . .

RUN pip install -r requirements.txt

# Django 애플리케이션 실행 "0.0.0.0:8000" 식으로 ip,port 설정가능
CMD python manage.py runserver 0.0.0.0:8000 & celery -A kingwangjjang worker --loglevel=info