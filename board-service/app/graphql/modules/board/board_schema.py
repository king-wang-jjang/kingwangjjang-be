import sys
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

import strawberry
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

import httpx
from app.db.context import Database
from bson import ObjectId
from pymongo import ReturnDocument
from app.services.count.views import get_views
# from app.services.board.index import tag
from app.services.board.pagination import get_pagination_daily_best
from app.services.board.pagination import get_pagination_real_time_best
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

from app.graphql.modules.board.board_type import Daily, Realtime, Comment,CommentEntrys, Like, SearchInput, SearchResult, View, ReplyEntrys
from strawberry.types import Info
from app.utils.auth_utils import get_authenticated_user_id

# Setup logger and exception hook
logger = setup_logger()
sys.excepthook = catch_exception

@strawberry.type
class Query:
    @strawberry.field
    def realtime_pagination(self, index: int = 0) -> List[Realtime]:
        return get_pagination_real_time_best(index)

    @strawberry.field
    def daily_pagination(self, index: int = 0) -> List[Daily]:
        return get_pagination_daily_best(index)

    @strawberry.field
    def get_views(self, board_id: str, site: str) -> View:
        return View(board_id=board_id,
                     site=site,
                     NOWVIEW=get_views(board_id, site))


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def search(self, input: SearchInput) -> List[SearchResult]:

        results = []

        return results
    
    @strawberry.mutation
    def add_like(self, board_id: str, info: Info) -> Like:
        try:
            # 간단 인증: 헬퍼 사용
            user_id = get_authenticated_user_id(info)

            collection = Database.get_collection('Realtime')
            try:
                oid = ObjectId(board_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid board_id")

            updated = collection.find_one_and_update(
                {"_id": oid},
                {"$inc": {"like_count": 1}},
                return_document=ReturnDocument.AFTER
            )

            if not updated:
                raise HTTPException(status_code=404, detail="Realtime document not found")

            now_like = int(updated.get("like_count", 0))
            return Like(board_id=board_id, site=updated.get("site", ""), likeCount=now_like)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
schema = strawberry.Schema(query=Query, mutation=Mutation)