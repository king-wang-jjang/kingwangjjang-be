celery -A app.celery_app.celery_app worker --loglevel=info &
poetry run uvicorn app.main:app