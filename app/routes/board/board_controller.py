from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from services.web_crwaling.index import tag
from services.web_crwaling.pagination import get_pagination_real_time_best,get_pagination_daily_best
from services.board_comment.add import board_comment_add
from services.board_comment.get import board_comment_get

from services.web_crwaling.index import board_summary
from utils.loghandler import setup_logger
from utils.loghandler import catch_exception
from typing import List, Optional,Dict
import sys
sys.excepthook = catch_exception
app = FastAPI()
logger = setup_logger()
router = APIRouter()
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
    def daily_pagination(self, index: int = 0) -> List[Daily]:
        try:
            # 여기에 실제 데이터 조회 로직 추가
            return get_pagination_daily_best(index)
        except Exception as e:
            logger.exception(f"Error getting daily data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
    @strawberry.field
    def realtime_pagination(self, index: int = 0) -> List[RealTime]:
        try:
            # print(get_pagination_real_time_best(index))
            return get_pagination_real_time_best(index)
        except Exception as e:
            logger.exception(f"Error getting realtime data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @strawberry.field
    def comment(self, board_id: str, site: str) -> Comment:
        try:

            # 여기에 실제 데이터 생성 로직 추가
            return Comment(board_id=board_id, site=site, Comments=board_comment_get(board_id, site))
        except Exception as e:
            logger.exception(f"Error creating summary board: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
@strawberry.type
class Mutation:
    @strawberry.field
    def summary_board(self, board_id: str, site: str) -> Summary:
        try:

            # 여기에 실제 데이터 생성 로직 추가
            return Summary(board_id=board_id, site=site, GPTAnswer=board_summary(board_id, site),Tag=list(tag(board_id, site)))
        except Exception as e:
            logger.exception(f"Error creating summary board: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @strawberry.field
    def comment(self, board_id: str, site: str, userid: str, comment: str) -> Comment:
        try:

            # 여기에 실제 데이터 생성 로직 추가
            return Comment(board_id=board_id, site=site, Comments=board_comment_add(board_id, site,userid,comment))
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