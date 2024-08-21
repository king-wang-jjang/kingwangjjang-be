# app/schema.py
import sys
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

import strawberry
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from strawberry.types import Info

from app.celery.count.tasks import task_likes_add
from app.celery.count.tasks import task_views_add
from app.celery.types import AddTaskTypes
from app.services.count import likes
from app.services.count import views
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

logger = setup_logger()


@strawberry.type
class Likes:
    """ """

    board_id: str
    site: str
    NOWLIKE: int


@strawberry.type
class Views:
    """ """

    board_id: str
    site: str
    NOWVIEW: int


@strawberry.type
class Daily:
    """ """

    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class RealTime:
    """ """

    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class Summary:
    """ """

    board_id: str
    site: str
    GPTAnswer: str
    Tag: List[str]


@strawberry.type
class Query:
    """ """

    @strawberry.field
    def hello2(self) -> str:
        """ """
        return "Hello, World!"


@strawberry.type
class Mutation:
    """ """

    @strawberry.field
    def likes_add(self, board_id: str, site: str) -> AddTaskTypes:
        """

        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:

        """
        task = task_likes_add.apply_async(board_id, site)
        return AddTaskTypes(task_id=task.id, status="Processing")

    @strawberry.field
    def views_add(self, board_id: str, site: str) -> AddTaskTypes:
        """

        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:

        """
        task = task_views_add.apply_async(board_id, site)
        return AddTaskTypes(task_id=task.id, status="Processing")


# @strawberry.type
# class TaskStatusQuery:
#     @strawberry.field
#     def task_status_views(self, task_id: str) -> TaskStatusType:
#         task_result = task_views_add.AsyncResult(task_id)
#
#         if task_result.state == "PENDING":
#             return TaskStatusType(status=task_result.state)
#         elif task_result.state != "FAILURE":
#             return TaskStatusType(status=task_result.state, result=str(task_result.result))
#         else:
#             return TaskStatusType(status=task_result.state, result=str(task_result.info))
#     @strawberry.field
#     def task_status_likes(self, task_id: str) -> TaskStatusType:
#         task_result = task_likes_add.AsyncResult(task_id)
#
#         if task_result.state == "PENDING":
#             return TaskStatusType(status=task_result.state)
#         elif task_result.state != "FAILURE":
#             return TaskStatusType(status=task_result.state, result=str(task_result.result))
#         else:
#             return TaskStatusType(status=task_result.state, result=str(task_result.info))
schema = strawberry.Schema(query=Query, mutation=Mutation)
# task_status_schema = strawberry.Schema(query=TaskStatusQuery)
