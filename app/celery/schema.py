import strawberry
from strawberry import Schema
from strawberry.tools import merge_types

import app.celery.LLM.schema
import app.routes.board.board_controller
import app.routes.comment.comment_comtroller
import app.routes.count.count_controller

Query = merge_types(
    "Query",
    (app.routes.board.board_controller.Query, ),
)
status_query = merge_types(
    "Query",
    (app.celery.LLM.schema.TaskStatusQuery, ),
    # app.celery.comment.schema.TaskStatusQuery),
)
Mutation = merge_types(
    "Mutation",
    (
        app.celery.LLM.schema.Mutation,
        app.routes.comment.comment_comtroller.Mutation,
        app.routes.count.count_controller.Mutation,
    ),
)
schema = Schema(query=Query, mutation=Mutation)
task_status_schema = Schema(query=status_query)
