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
from app.services.count.likes import get_likes
from app.services.count.views import get_views
# from app.services.board.index import tag
from app.services.board.pagination import get_pagination_daily_best
from app.services.board.pagination import get_pagination_real_time_best
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

from app.graphql.modules.board.board_type import Daily, Realtime, Comment,CommentEntrys, Like, SearchInput, SearchResult, View, ReplyEntrys

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
    def comment(self, board_id: str, site: str) -> Comment:
        try:
            # delegate to comment-service via API Gateway prefix
            # When running locally, API Gateway maps commentservice/ -> localhost:33335
            url = f"http://localhost:8000/commentservice/comment?board_id={board_id}&site={site}"
            with httpx.Client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                comments = resp.json()
            if not comments:
                comments = [{"none": "none"}]
            datas = []
            for comment in comments:
                tmp_replys = []
                for data in comment["reply"]:
                    logger.debug(f"Reply to comment {data}")
                    tmp_replys.append(ReplyEntrys(board_id=data["board_id"], site=data["site"], user_id=data["user_id"],
                                                  comment=data["comment"], timestamp=data["timestamp"]))
                datas.append(
                    CommentEntrys(
                        _id=comment["_id"],
                        board_id=data["board_id"],
                        site=data["site"],
                        user_id=data["user_id"],
                        comment=data["comment"],
                        reply=tmp_replys,
                        timestamp=data["timestamp"]
                    )
                )
            return Comment(board_id=board_id,
                           site=site,
                           Comments=datas)
        except Exception as e:
            logger.exception(f"Error creating summary board: {e}")
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    @strawberry.field
    def get_like(self, board_id: str, site: str) -> Like:
        return Like(board_id=board_id,
                     site=site,
                     NOWLIKE=get_likes(board_id, site))

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
    
schema = strawberry.Schema(query=Query, mutation=Mutation)