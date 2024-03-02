
# 이미지 기반이 될 베이스 이미지
FROM python:3

ENV PYTHONUNBUFFERED 1

# 작업디렉토리 설정
WORKDIR /web

# 소스코드 복사
COPY . .

# 라이브러리 설치
RUN pip install -r requirements.txt

# Django 애플리케이션 실행 "0.0.0.0:8000" 식으로 ip,port 설정가능
CMD [ "python", "manage.py", "runserver" ]