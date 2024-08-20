import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

import strawberry
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

from app.services.board_comment.get import board_comment_get
from app.services.count.likes import get_likes
from app.services.count.views import get_views
from app.services.web_crawling.index import tag
from app.services.web_crawling.pagination import (
    get_pagination_daily_best, get_pagination_real_time_best)
from app.utils.loghandler import catch_exception, setup_logger

# Setup logger and exception hook
logger = setup_logger()
sys.excepthook = catch_exception

# Initialize FastAPI app
app = FastAPI()
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
    GPTAnswer: str
    Tag: List[str]


@strawberry.type
class Comment:
    board_id: str
    site: str
    Comments: str


@strawberry.type
class Likes:
    board_id: str
    site: str
    NOWLIKE: int


@strawberry.type
class Views:
    board_id: str
    site: str
    NOWVIEW: int


@strawberry.type
class Query:
    @strawberry.field
    def daily_pagination(self, index: int = 0) -> List[Daily]:
        try:
            return get_pagination_daily_best(index)
        except Exception as e:
            logger.exception(f"Error getting daily data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @strawberry.field
    def realtime_pagination(self, index: int = 0) -> List[RealTime]:
        try:
            return get_pagination_real_time_best(index)
        except Exception as e:
            logger.exception(f"Error getting realtime data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @strawberry.field
    def comment(self, board_id: str, site: str) -> Comment:
        try:
            comments = board_comment_get(board_id, site)
            if not comments:
                comments = [{"none": "none"}]
            return Comment(board_id=board_id, site=site, Comments=str(comments))
        except Exception as e:
            logger.exception(f"Error creating summary board: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @strawberry.field
    def get_like(self, board_id: str, site: str) -> Likes:
        return Likes(board_id=board_id, site=site, NOWLIKE=get_likes(board_id, site))

    @strawberry.field
    def get_views(self, board_id: str, site: str) -> Views:
        return Views(board_id=board_id, site=site, NOWVIEW=get_views(board_id, site))


# Initialize GraphQL schema and router
schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema=schema)
app.include_router(router)
app.include_router(graphql_app, prefix="/graphql")
