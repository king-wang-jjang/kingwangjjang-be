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

from app.services.board_comment.get import board_comment_get
from app.services.count.likes import get_likes
from app.services.count.views import get_views
from app.services.web_crawling.index import tag
from app.services.web_crawling.pagination import get_pagination_daily_best
from app.services.web_crawling.pagination import get_pagination_real_time_best
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

from app.types.board_type import Daily, Realtime, Comment,CommentEntrys, Like, View, ReplyEntrys

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
            comments = board_comment_get(board_id, site)
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


schema = strawberry.Schema(query=Query)