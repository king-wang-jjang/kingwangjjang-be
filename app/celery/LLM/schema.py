# app/schema.py
from datetime import datetime
from typing import Dict, List, Optional

import strawberry
from strawberry.types import Info

from app.celery.LLM.tasks import task_summary_board
from app.celery.types import AddTaskTypes, TaskStatusType


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
    def hello(self) -> str:
        """ """
        return "Hello, World!"


@strawberry.type
class Mutation:
    """ """

    @strawberry.mutation
    def summary_board(self, board_id: str, site: str) -> AddTaskTypes:
        """

        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:

        """
        task = task_summary_board.apply_async((board_id, site))
        print(task)

        return AddTaskTypes(task_id=task.id, status="Processing")

    # @strawberry.mutation
    # def comment(self, board_id: str, site: str, userid: str, comment: str) -> AddTaskType:
    #     task = task_board_comment_add.apply_async(board_id,site,userid,comment)
    #     return AddTaskType(task_id=task.id, status="Processing")
    # try:
    #
    #     # 여기에 실제 데이터 생성 로직 추가
    #     return Summary(board_id=board_id, site=site, GPTAnswer=board_summary(board_id, site),Tag=list(tag(board_id, site)))
    # except Exception as e:
    #     logger.exception(f"Error creating summary board: {e}")
    #     raise HTTPException(status_code=500, detail="Internal server error")


@strawberry.type
class TaskStatusQuery:
    """ """

    @strawberry.field
    def task_status_llm(self, task_id: str) -> TaskStatusType:
        """

        :param task_id: str:
        :param task_id: str:

        """
        task_result = task_summary_board.AsyncResult(task_id)

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
