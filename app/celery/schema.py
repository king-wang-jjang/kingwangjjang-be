import app.celery.LLM.schema
import app.celery.comment.schema
from strawberry import Schema
from strawberry.tools import merge_types
Query = merge_types("Query", (app.celery.LLM.schema.Query, app.celery.comment.schema.Query))
status_query = merge_types("Query", (app.celery.LLM.schema.TaskStatusQuery, app.celery.comment.schema.TaskStatusType))
Mutation = merge_types("Mutation", (app.celery.LLM.schema.Mutation, app.celery.comment.schema.Mutation))
schema = Schema(query=Query, mutation=Mutation)
task_status_schema = Schema(query=status_query)