import app.celery.LLM.schema
import app.celery.comment.schema
import app.celery.count.schema
import app.routes.board.board_controller
from strawberry import Schema
import strawberry

from strawberry.tools import merge_types

Query = merge_types(
    "Query",
    (
        app.celery.LLM.schema.Query,
        app.celery.comment.schema.Query,
        app.routes.board.board_controller.Query,
        app.celery.count.schema.Query,
    ),
)
status_query = merge_types(
    "Query",
    (app.celery.LLM.schema.TaskStatusQuery, app.celery.comment.schema.TaskStatusQuery),
)
Mutation = merge_types(
    "Mutation",
    (
        app.celery.LLM.schema.Mutation,
        app.celery.comment.schema.Mutation,
        app.celery.count.schema.Mutation,
    ),
)
schema = Schema(query=Query, mutation=Mutation)
task_status_schema = Schema(query=status_query)
