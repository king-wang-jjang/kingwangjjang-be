celery -A app.celery.celery_app worker --loglevel=info &
poetry run python main.py