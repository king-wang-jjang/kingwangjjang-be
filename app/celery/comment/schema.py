# app/schema.py
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

import strawberry
from strawberry.types import Info

from app.celery.comment.tasks import task_board_comment_add
from app.celery.comment.tasks import task_board_reply_add
from app.celery.types import AddTaskTypes
from app.celery.types import TaskStatusType


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
class Comment:
    """ """

    board_id: str
    site: str
    Comments: List[Dict]


@strawberry.type
class Query:
    """ """

    @strawberry.field
    def hellos(self) -> str:
        """ """
        return "Hello, World!"


@strawberry.type
class Mutation:
    """ """

    @strawberry.mutation
    def comment(
        self, board_id: str, site: str, userid: str, comment: str
    ) -> AddTaskTypes:
        """

        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:
        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:
        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:
        :param board_id: str: 
        :param site: str: 
        :param userid: str: 
        :param comment: str: 

        """
        task = task_board_comment_add.apply_async(
            kwargs={
                "board_id": board_id,
                "site": site,
                "userid": userid,
                "comment": comment,
            }
        )
        return AddTaskTypes(task_id=task.id, status="Processing")

    @strawberry.mutation
    def reply(
        self, board_id: str, site: str, userid: str, parents_comment: str, reply: str
    ) -> AddTaskTypes:
        """

        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param parents_comment: str:
        :param reply: str:
        :param board_id: str: 
        :param site: str: 
        :param userid: str: 
        :param parents_comment: str: 
        :param reply: str: 

        """
        task = task_board_reply_add.apply_async(
            board_id, site, userid, parents_comment, reply
        )
        return AddTaskTypes(task_id=task.id, status="Processing")


@strawberry.type
class TaskStatusQuery:
    """ """

    @strawberry.field
    def task_status_comment(self, task_id: str) -> TaskStatusType:
        """

        :param task_id: str:
        :param task_id: str:
        :param task_id: str:
        :param task_id: str: 

        """
        task_result = task_board_comment_add.AsyncResult(task_id)

        if task_result.state == "PENDING":
            return TaskStatusType(status=task_result.state)
        elif task_result.state != "FAILURE":
            return TaskStatusType(
                status=task_result.state, result=str(task_result.result)
            )
        else:
            return TaskStatusType(
                status=task_result.state, result=str(task_result.info)
            )


schema = strawberry.Schema(query=Query, mutation=Mutation)
task_status_schema = strawberry.Schema(query=TaskStatusQuery)
