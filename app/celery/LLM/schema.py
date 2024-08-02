# app/schema.py

import strawberry
from strawberry.types import Info

from .tasks import example_task

@strawberry.type
class AddTaskType:
    task_id: str
    status: str

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello, World!"

@strawberry.type
class Mutation:
    @strawberry.mutation
    def add(self, x: int, y: int) -> AddTaskType:
        task = example_task.apply_async((x, y))
        print(task)

        return AddTaskType(task_id=task.id, status="Processing")

@strawberry.type
class TaskStatusType:
    status: str
    result: str = None

@strawberry.type
class TaskStatusQuery:
    @strawberry.field
    def task_status(self, task_id: str) -> TaskStatusType:
        task_result = example_task.AsyncResult(task_id)

        if task_result.state == "PENDING":
            return TaskStatusType(status=task_result.state)
        elif task_result.state != "FAILURE":
            return TaskStatusType(status=task_result.state, result=str(task_result.result))
        else:
            return TaskStatusType(status=task_result.state, result=str(task_result.info))
schema = strawberry.Schema(query=Query, mutation=Mutation)
task_status_schema = strawberry.Schema(query=TaskStatusQuery)