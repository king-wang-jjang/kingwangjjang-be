from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.celery.tasks"],
)

celery_app.conf.update(
    task_routes={
        "app.celery.tasks.task_realtime_to_db": {"queue": "crawling_queue"},
    },
    result_expires=3600,
    beat_schedule={
        'realtime-to-db-every-5-minutes': {
            'task': 'app.celery.tasks.task_realtime_to_db',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
    },
)

if __name__ == "__main__":
    celery_app.start()