from celery import Celery

celery_app = Celery(
    "worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.service.web_crawling.tasks"],
)

celery_app.conf.update(
    task_routes={
        "app.tasks.example_task": {"queue": "realtime_to_db_queue"},
    },
    result_expires=3600,
)

if __name__ == "__main__":
    celery_app.start()