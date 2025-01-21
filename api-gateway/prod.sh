#celery -A app.celery.celery_app worker --loglevel=debug -E &
#celery -A app.celery.celery_app beat --loglevel=debug &
# poetry run python app/main.py
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

 