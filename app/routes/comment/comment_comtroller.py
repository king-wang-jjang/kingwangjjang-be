# app/count_controller.py
from datetime import datetime
from typing import List
from typing import Optional
import strawberry
from app.services.board_comment.add import board_comment_add
from app.services.board_comment.add import board_reply_add


@strawberry.type
class ReplyEntry:
    """ReplyEntry represents a reply to a comment"""

    board_id: str
    site: str
    user_id: str
    comment: str
    timestamp: str
    _id: str


@strawberry.type
class CommentEntry:
    _id: str
    board_id: str
    site: str
    user_id: str
    comment: str
    reply: str
    timestamp: str


# 답글(Reply) 엔트리 정의


@strawberry.type
class Daily:
    """ """

    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class RealTime:
    """ """

    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class Summary:
    """ """

    board_id: str
    site: str
    GPTAnswer: str
    Tag: List[str]


@strawberry.type
class BoardComment:
    """ """

    comments: List[CommentEntry]  # Dict의 타입을 명시적으로 지정


@strawberry.type
class BoardReply:
    """ """

    replies: List[ReplyEntry]  # Use a specific Strawberry type


@strawberry.type
class Mutation:
    """ """

    @strawberry.mutation
    def comment(
        self, board_id: str, site: str, userid: str, comment: str
    ) -> BoardComment:
        """

        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:

        """

        return BoardComment(comments=board_comment_add(board_id, site, userid, comment))

    @strawberry.mutation
    def reply(
        self, board_id: str, site: str, userid: str, parents_comment: str, reply: str
    ) -> CommentEntry:
        """

        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param parents_comment: str:
        :param reply: str:

        """
        reply_dicts = board_reply_add(
            board_id=board_id,
            site=site,
            userid=userid,
            parrent_comment=parents_comment,
            reply=reply,
        )
        # Convert each dict to a ReplyEntry instance
        return CommentEntry(
            _id=reply_dicts[0]["_id"],
            board_id=reply_dicts[0]["board_id"],
            user_id=reply_dicts[0]["user_id"],
            comment=reply_dicts[0]["comment"],
            reply=str(reply_dicts[0]["reply"]),
            timestamp=reply_dicts[0]["timestamp"],
            site=reply_dicts[0]["site"],
        )
