FROM python:3.12.4-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.5

COPY ./pyproject.toml ./poetry.lock ./poetry.toml /app/
RUN poetry install --only main --no-root

COPY . /app
RUN sed -i 's/\r$//' /app/prod.sh && chmod +x /app/prod.sh

EXPOSE 33336

ENTRYPOINT ["sh", "prod.sh"]
