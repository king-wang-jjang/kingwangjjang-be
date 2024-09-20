# Python 3.12.4 이미지 사용
FROM python:3.12.4

# 디렉토리 설정
WORKDIR /app

## requirements.txt 파일을 /app 디렉토리로 복사
#COPY ./requirements.txt /code/requirements.txt

#poetry 설치
RUN pip install poetry

#poetry 관련 파일 복사
COPY ./pyproject.toml ./poetry.lock* /app/

RUN poetry cache clear --all pypi

# 필요 라이브러리 설치
RUN poetry lock --no-update && poetry install --only main

#소스코드 복사
COPY . .

#3000번 포트 개방.
EXPOSE 8000
# uvicorn 서버 실행
ENTRYPOINT  ["poetry","run", "sh", "prod.sh"]
