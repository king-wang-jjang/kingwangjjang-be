# app/tasks.py

from app.services.web_crawling.index import get_real_time_best
from .celery_app import celery_app

@celery_app.task
def task_realtime_to_db():
    print("task_realtime_to_db")
    return get_real_time_best()