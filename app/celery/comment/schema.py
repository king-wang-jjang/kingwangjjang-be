# app/schema.py

import strawberry
from strawberry.types import Info
from app.celery.types import TaskStatusType
from app.celery.types import AddTaskTypes

from app.celery.comment.tasks import task_board_comment_add
from typing import List, Optional, Dict
from datetime import datetime


@strawberry.type
class Daily:
    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class RealTime:
    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class Summary:
    board_id: str
    site: str
    GPTAnswer: str
    Tag: List[str]


@strawberry.type
class Comment:
    board_id: str
    site: str
    Comments: List[Dict]


@strawberry.type
class Query:
    @strawberry.field
    def hellos(self) -> str:
        return "Hello, World!"


@strawberry.type
class Mutation:

    @strawberry.mutation
    def comment(self, board_id: str, site: str, userid: str, comment: str) -> AddTaskTypes:
        task = task_board_comment_add.apply_async(
            board_id, site, userid, comment)
        return AddTaskTypes(task_id=task.id, status="Processing")


@strawberry.type
class TaskStatusQuery:
    @strawberry.field
    def task_status_comment(self, task_id: str) -> TaskStatusType:
        task_result = task_board_comment_add.AsyncResult(task_id)

        if task_result.state == "PENDING":
            return TaskStatusType(status=task_result.state)
        elif task_result.state != "FAILURE":
            return TaskStatusType(status=task_result.state, result=str(task_result.result))
        else:
            return TaskStatusType(status=task_result.state, result=str(task_result.info))


schema = strawberry.Schema(query=Query, mutation=Mutation)
task_status_schema = strawberry.Schema(query=TaskStatusQuery)
