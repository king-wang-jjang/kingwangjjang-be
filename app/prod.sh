#celery -A app.celery.celery_app worker --loglevel=debug -E &
poetry run python app/main.py
