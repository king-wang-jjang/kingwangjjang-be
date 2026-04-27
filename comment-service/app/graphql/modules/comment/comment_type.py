from datetime import datetime
from typing import List, Optional
import strawberry


@strawberry.type
class CommentEntry:
    _id: str
    board_id: str
    parent_id: Optional[str]  # 부모 댓글 ID (최상위면 null)
    content: str
    user_id: str
    user_nickname: Optional[str]  # 사용자 닉네임
    like_count: int          # 좋아요 수
    is_liked: bool           # 현재 요청 사용자가 좋아요 했는지 여부
    reply_count: int         # 직계 자식 수 (대댓글 수)
    is_deleted: bool         # 소프트 삭제 여부
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CommentList:
    board_id: str
    comments: List[CommentEntry]
    total_count: int


@strawberry.input
class CreateCommentInput:
    board_id: str
    parent_id: Optional[str] = None  # 대댓글인 경우 부모 댓글 ID
    content: str


@strawberry.input
class UpdateCommentInput:
    comment_id: str
    content: str


@strawberry.input
class DeleteCommentInput:
    comment_id: str
