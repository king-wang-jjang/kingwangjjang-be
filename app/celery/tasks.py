# app/tasks.py

from .celery_app import celery_app
from app.services.web_crawling.index import get_real_time_best, get_daily_best
from app.services.web_crawling.pagination import get_pagination_real_time_best, get_pagination_daily_best
from app.services.web_crawling.index import tag, board_summary
from app.services.count.likes import add_likes, get_likes
from app.services.count.views import add_views, get_views
from app.utils.uptimerobot import check_online

from app.services.board_comment.add import board_comment_add
from app.services.board_comment.get import board_comment_get
import requests


@celery_app.task
def task_realtime_to_db():
    print("task_realtime_to_db")
    return get_real_time_best()


@celery_app.task
def task_daily_to_web():
    print("task_daily_to_web")
    return get_daily_best()


@celery_app.task
def auto_reboot():
    return check_online()


@celery_app.task
def task_add_views(board_id: str, site: str):
    return add_views(board_id, site)


@celery_app.task
def task_add_likes(board_id: str, site: str):
    return add_likes(board_id, site)
