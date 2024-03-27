
# 이미지 기반이 될 베이스 이미지
FROM python:3

ENV PYTHONUNBUFFERED 1

# 작업디렉토리 설정
WORKDIR /web

# 소스코드 복사
COPY . .

# 라이브러리 설치
RUN apt-get -y update && \
    apt-get -y install wget unzip curl && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get -y install ./google-chrome-stable_current_amd64.deb && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip chromedriver -d /usr/bin && \
    rm /tmp/chromedriver.zip
    
# 라이브러리 설치
RUN pip install -r requirements.txt

# Django 애플리케이션 실행 "0.0.0.0:8000" 식으로 ip,port 설정가능
CMD [ "python", "manage.py", "runserver" , "0.0.0.0:8000"]
# ip:port 를 설정하지 않으면 localhost로 동작한다.