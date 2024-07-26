from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from services.web_crwaling.views import board_summary
from utils.loghandler import setup_logger

app = FastAPI()
logger = setup_logger()
router = APIRouter(
    prefix="/board",
    tags=["Boards"]
)
@strawberry.type
class Daily:
    board_id: str
    rank: str
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None

@strawberry.type
class Query:
    @strawberry.field
    def all_daily(self) -> List[Daily]:
        try:
            return []  # 예시 데이터 반환
        except Exception as e:
            logger.exception(f"Error getting daily data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

@strawberry.type
class Mutation:
    @strawberry.field
    def summary_board(self, board_id: str, site: str) -> Daily:
        try:
            # 여기에 실제 데이터 생성 로직 추가
            return Daily(board_id=board_id, rank="1", site=site, title="Example Title", url="http://example.com", create_time=datetime.now())
        except Exception as e:
            logger.exception(f"Error creating summary board: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

schema = strawberry.Schema(query=Query, mutation=Mutation)

@app.post("/graphql")
async def graphql_endpoint(request: Request):
    data = await request.json()
    response = schema.execute_sync(data["query"])
    if response.errors:
        raise HTTPException(status_code=400, detail=str(response.errors[0]))
    return response.data

graphql_app = GraphQLRouter(schema)
router.include_router(graphql_app, prefix="/graphql")