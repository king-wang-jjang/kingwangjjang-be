# app/tasks.py
from app.services.count import likes, views

from ...services.count.likes import add_likes
from ...services.count.views import add_views
from ..celery_app import celery_app


@celery_app.task
def task_likes_add(board_id: str, site: str):
    """

    :param board_id: str:
    :param site: str:
    :param board_id: str:
    :param site: str:

    """
    return add_likes(board_id, site)


@celery_app.task
def task_views_add(board_id: str, site: str):
    """

    :param board_id: str:
    :param site: str:
    :param board_id: str:
    :param site: str:

    """
    return add_views(board_id, site)
