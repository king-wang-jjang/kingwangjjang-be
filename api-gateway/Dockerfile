# Python 3.12.4 이미지 사용
FROM python:3.12.4

# 디렉토리 설정
WORKDIR /app

# Poetry 설치
RUN pip install --no-cache-dir poetry
RUN apt-get update -y && apt-get install -y libgl1-mesa-glx

# Poetry 관련 파일 복사
COPY ./pyproject.toml /app/
COPY ./poetry.lock /app/  
# poetry.lock 파일이 있는 경우만 복사

# 필요 라이브러리 설치
RUN poetry install --only main --no-root --no-interaction

# 소스코드 복사
COPY . .

# 실행 파일 권한 설정 (prod.sh가 실행 가능해야 함)
RUN chmod +x prod.sh

# 포트 노출
EXPOSE 8000

# uvicorn 서버 실행
ENTRYPOINT ["poetry", "run", "sh", "prod.sh"]
