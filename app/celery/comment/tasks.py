# app/tasks.py

from ..celery_app import celery_app
from app.services.board_comment.add import board_comment_add

@celery_app.task
def task_board_comment_add(board_id : str, site : str,userid : str,comment: str):
    return board_comment_add(board_id,site,userid,comment)