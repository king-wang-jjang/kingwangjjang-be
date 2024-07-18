# Python 3.12.4 이미지 사용
FROM python:3.12.4

# 디렉토리 설정
WORKDIR /code

# requirements.txt 파일을 /app 디렉토리로 복사
COPY ./requirements.txt /code/requirements.txt

# 필요 라이브러리 설치
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY app .

# uvicorn 서버 실행
CMD ["sh", "dev.bash"]