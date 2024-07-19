import strawberry
from fastapi import FastAPI, APIRouter
from strawberry.asgi import GraphQL
import datetime

@strawberry.type
class ID:
    site: str  # (dcinside | ygosu | ppomppu)
    title: str
    url: str
    createTime: datetime.datetime
    GPTAnswer: str

@strawberry.type
class Post:
    summary: str
    imgs: list

@strawberry.type
class Query:
    @strawberry.field
    def post(self) -> ID:
        #예시대이터를 넣어놨으나 실제 대이터로 변경요함.
        return ID(
            site="dcinside",
            title="Example Title",
            url="https://gall.dcinside.com/board/view/?id=dcbest&no=248716",
            createTime=datetime.datetime.now(),
            GPTAnswer="gpt 응답"
        )


# 스키마 정의
schema = strawberry.Schema(query=Query)

# FastAPI 앱 생성
app = FastAPI()

# APIRouter 생성
router = APIRouter()

# GraphQL 엔드포인트 설정
graphql_app = GraphQL(schema)
router.add_route("/graphql", graphql_app)
router.add_websocket_route("/graphql", graphql_app)


