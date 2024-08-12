# app/tasks.py

from .celery_app import celery_app
from app.services.web_crawling.index import get_real_time_best,get_daily_best
from app.services.web_crawling.pagination import get_pagination_real_time_best,get_pagination_daily_best
from app.services.web_crawling.index import tag,board_summary
@celery_app.task
def task_realtime_to_db():
    print("task_realtime_to_db")
    return get_real_time_best()

@celery_app.task
def task_daily_to_web():
    print("task_daily_to_web")
    return get_daily_best()

@celery_app.task
def task_summary_board(board_id: str, site: str):
    return (board_id, site, board_summary(board_id, site),list(tag(board_id, site)))