from datetime import datetime
from typing import Any, List, Optional, Tuple, Union
import strawberry

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
    # reply: List[ReplyEntrys]
    timestamp: str

@strawberry.type
class Realtime:
    _id: Optional[str] = None
    board_id: Tuple[str, int]
    # rank: Optional[str] = None
    site: str
    title: str
    url: str
    contents: Optional[str] = None
    gpt_answer: Optional[str] = None
    create_time: datetime
@strawberry.type
class Summary:
    board_id: str
    site: str
    gpt_answer: str
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