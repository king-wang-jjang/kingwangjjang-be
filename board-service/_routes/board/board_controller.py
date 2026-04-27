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
from app.services.count.likes import get_likes_info, toggle_like
from app.services.count.views import get_views
from app.services.web_crawling.index import tag
from app.services.web_crawling.pagination import get_pagination_daily_best
from app.services.web_crawling.pagination import get_pagination_real_time_best
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

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
    gpt_answer: Optional[str] = None

@strawberry.type
class ReplyEntrys:
    board_id: str
    site: str
    user_id: str
    comment: str
    timestamp: str

@strawberry.type
class CommentEntrys:
    _id: str
    board_id: str
    site: str
    user_id: str
    comment: str
    reply: List[ReplyEntrys]
    timestamp: str

@strawberry.type
class Realtime:
    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    gpt_answer: Optional[str] = None

@strawberry.type
class Summary:
    board_id: str
    site: str
    gpt_answer: str
    Tag: List[str]

@strawberry.type
class Comment:
    board_id: str
    site: str
    Comments: List[CommentEntrys]

@strawberry.type
class Like:
    board_id: str
    site: str
    total_likes: int
    is_liked: bool

@strawberry.type
class View:
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
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    @strawberry.field
    def realtime_pagination(self, index: int = 0) -> List[Realtime]:
        try:
            return get_pagination_real_time_best(index)
        except Exception as e:
            logger.exception(f"Error getting realtime data: {e}")
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    @strawberry.field
    def comment(self, board_id: str, site: str) -> Comment:
        try:
            import httpx
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
    def get_likes_info(self, board_id: str, site: str, user_id: Optional[str] = None) -> Like:
        likes_info = get_likes_info(board_id, site, user_id)
        return Like(
            board_id=board_id,
            site=site,
            total_likes=likes_info['total_likes'],
            is_liked=likes_info['is_liked']
        )

    @strawberry.field
    def get_views(self, board_id: str, site: str) -> View:
        return View(board_id=board_id,
                     site=site,
                     NOWVIEW=get_views(board_id, site))


@strawberry.type
class Mutation:
    @strawberry.mutation
    def toggle_like(self, board_id: str, site: str, user_id: str) -> Like:
        if not user_id:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        
        updated_likes_info = toggle_like(board_id, site, user_id)
        return Like(
            board_id=board_id,
            site=site,
            total_likes=updated_likes_info['total_likes'],
            is_liked=updated_likes_info['is_liked']
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema=schema)
