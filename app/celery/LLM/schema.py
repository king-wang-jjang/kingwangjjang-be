# app/schema.py

import strawberry
from strawberry.types import Info

from ..tasks import task_summary_board
from typing import List, Optional,Dict
from datetime import datetime

@strawberry.type
class AddTaskType:
    task_id: str
    status: str
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
    GPTAnswer : str
    Tag : List[str]
@strawberry.type
class Comment:
    board_id: str
    site: str
    Comments : List[Dict]
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello, World!"


@strawberry.type
class Mutation:

    @strawberry.mutation
    def summary_board(self, board_id: str, site: str) -> AddTaskType:
        task = task_summary_board.apply_async((board_id,site))
        print(task)

        return AddTaskType(task_id=task.id, status="Processing")
        # try:
        #
        #     # 여기에 실제 데이터 생성 로직 추가
        #     return Summary(board_id=board_id, site=site, GPTAnswer=board_summary(board_id, site),Tag=list(tag(board_id, site)))
        # except Exception as e:
        #     logger.exception(f"Error creating summary board: {e}")
        #     raise HTTPException(status_code=500, detail="Internal server error")

@strawberry.type
class TaskStatusType:
    status: str
    result: str = None

@strawberry.type
class TaskStatusQuery:
    @strawberry.field
    def task_status(self, task_id: str) -> TaskStatusType:
        task_result = task_summary_board.AsyncResult(task_id)

        if task_result.state == "PENDING":
            return TaskStatusType(status=task_result.state)
        elif task_result.state != "FAILURE":
            return TaskStatusType(status=task_result.state, result=str(task_result.result))
        else:
            return TaskStatusType(status=task_result.state, result=str(task_result.info))
schema = strawberry.Schema(query=Query, mutation=Mutation)
task_status_schema = strawberry.Schema(query=TaskStatusQuery)