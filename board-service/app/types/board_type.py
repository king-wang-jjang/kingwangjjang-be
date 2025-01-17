from datetime import datetime
from typing import Optional
import strawberry

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
    # reply: List[ReplyEntrys]
    timestamp: str

@strawberry.type
class Realtime:
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
    # Tag: List[str]

@strawberry.type
class Comment:
    board_id: str
    site: str
    # Comments: List[CommentEntrys]

@strawberry.type
class Like:
    board_id: str
    site: str
    NOWLIKE: int

@strawberry.type
class View:
    board_id: str
    site: str
    NOWVIEW: int