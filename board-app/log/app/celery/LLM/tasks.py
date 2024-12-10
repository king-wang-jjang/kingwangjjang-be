# app/tasks.py

from ..celery_app import celery_app
from app.services.web_crawling.index import tag,board_summary

@celery_app.task
def task_summary_board(board_id: str, site: str):
    return (board_id, site, board_summary(board_id, site),list(tag(board_id, site)))
