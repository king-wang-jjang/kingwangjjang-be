import LLM.schema
import comment.schema
from strawberry import Schema
from strawberry.tools import merge_types
Query = merge_types("Query", (LLM.schema.Query, comment.schema.Query))
status_query = merge_types("Query", (LLM.schema.TaskStatusQuery, comment.schema.TaskStatusType))
Mutation = merge_types("Mutation", (LLM.schema.Mutation, comment.schema.Mutation))
schema = Schema(query=Query, mutation=Mutation)
task_status_schema = Schema(query=status_query)