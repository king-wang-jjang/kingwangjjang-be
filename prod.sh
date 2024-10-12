celery -A app.celery.celery_app worker --loglevel=debug -E &
#celery -A app.celery.celery_app beat --loglevel=debug &
poetry run python app/main.py
