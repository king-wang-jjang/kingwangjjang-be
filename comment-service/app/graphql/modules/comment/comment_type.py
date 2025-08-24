from datetime import datetime
from typing import List, Optional
import strawberry


@strawberry.type
class ReplyEntry:
    board_id: str
    site: str
    user_id: str
    comment: str
    timestamp: datetime


@strawberry.type
class CommentEntry:
    _id: str
    board_id: str
    site: str
    user_id: str
    comment: str
    reply: List[ReplyEntry]
    timestamp: datetime


@strawberry.type
class Comment:
    board_id: str
    site: str
    comments: List[CommentEntry]

