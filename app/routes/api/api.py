# import strawberry
# from fastapi import APIRouter
# from strawberry.fastapi import GraphQLRouter
# import datetime
# from typing import List
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
# @strawberry.type
# class ID:
#     site: str  # (dcinside | ygosu | ppomppu)
#     title: str
#     url: str
#     createTime: datetime.datetime
#     GPTAnswer: str

# @strawberry.type
# class Post:
#     summary: str
#     imgs: List[str]

# @strawberry.type
# class Query:
#     @strawberry.field
#     def post(self) -> ID:
#         return ID(
#             site="dcinside",
#             title="Example Title",
#             url="https://gall.dcinside.com/board/view/?id=dcbest&no=248716",
#             createTime=datetime.datetime.now(),
#             GPTAnswer="gpt 응답"
#         )

# # Define schema
# schema = strawberry.Schema(query=Query)

# # Create APIRouter
# router = APIRouter()

# # Create GraphQL router and include it
# graphql_app = GraphQLRouter(schema)
# router.include_router(graphql_app, prefix="/graphql")
