
# 이미지 기반이 될 베이스 이미지
FROM python:3

ENV PYTHONUNBUFFERED 1

# Chromedriver 다운로드 및 설치
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Chrome 브라우저 설치
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

RUN chmod +x /usr/bin/google-chrome-stable

# Chromedriver 설치
RUN wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/94.0.4606.61/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip

RUN chmod +x /usr/local/bin/chromedriver

# 작업디렉토리 설정
WORKDIR /web

# 소스코드 복사
COPY . .

RUN pip install -r requirements.txt

# Django 애플리케이션 실행 "0.0.0.0:8000" 식으로 ip,port 설정가능
CMD [ "python", "manage.py", "runserver" , "0.0.0.0:8000"]
# ip:port 를 설정하지 않으면 localhost로 동작한다.