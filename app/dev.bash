celery -A app.celery.celery_app worker --loglevel=info &
poetry run uvicorn app.main:app --reload