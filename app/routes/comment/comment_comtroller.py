from datetime import datetime
from typing import List, Optional
import strawberry
from app.services.board_comment.add import board_comment_add, board_reply_add
from app.utils.loghandler import setup_logger

# Logger 설정
logger = setup_logger()


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
    """CommentEntry represents a comment on a board"""
    _id: str
    board_id: str
    site: str
    user_id: str
    comment: str
    reply: str
    timestamp: str


@strawberry.type
class Daily:
    """Represents a daily entry"""
    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class RealTime:
    """Represents a real-time entry"""
    board_id: str
    rank: Optional[str] = None
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: Optional[str] = None


@strawberry.type
class Summary:
    """Represents a summary entry"""
    board_id: str
    site: str
    GPTAnswer: str
    Tag: List[str]


@strawberry.type
class BoardComment:
    """Represents a list of comments on a board"""
    comments: List[CommentEntry]


@strawberry.type
class BoardReply:
    """Represents a list of replies to a comment"""
    replies: List[ReplyEntry]


@strawberry.type
class Mutation:
    """Mutation class for adding comments and replies"""

    @strawberry.mutation
    def comment(self, board_id: str, site: str, userid: str, comment: str) ->  CommentEntry:
        """
        Add a comment to a board.

        :param board_id: ID of the board
        :param site: Site name
        :param userid: ID of the user posting the comment
        :param comment: The comment text
        :return: A BoardComment object containing the added comment
        """
        logger.info(f"Adding comment to board {board_id} on site {site} by user {userid}")
        try:
            comment_data = board_comment_add(board_id, site, userid, comment)
            logger.info(f"Comment added to board {board_id}")
            return CommentEntry(
                _id=comment_data[0]["_id"],
                board_id=comment_data[0]["board_id"],
                user_id=comment_data[0]["user_id"],
                comment=comment_data[0]["comment"],
                timestamp=comment_data[0]["timestamp"],
                site=comment_data[0]["site"]
            )
        except Exception as e:
            logger.error(f"Error adding comment to board {board_id} on site {site}: {e}")
            raise e

    @strawberry.mutation
    def reply(self, board_id: str, site: str, userid: str, parents_comment: str, reply: str) -> CommentEntry:
        """
        Add a reply to an existing comment.

        :param board_id: ID of the board
        :param site: Site name
        :param userid: ID of the user posting the reply
        :param parents_comment: ID of the parent comment to reply to
        :param reply: The reply text
        :return: A CommentEntry object representing the updated parent comment
        """
        logger.info(f"Adding reply to comment {parents_comment} on board {board_id} by user {userid}")
        try:
            reply_dicts = board_reply_add(board_id=board_id, site=site, userid=userid,
                                          parent_comment=parents_comment, reply=reply)
            logger.info(f"Reply added to comment {parents_comment} on board {board_id}")

            # Convert reply_dicts to a CommentEntry object
            return CommentEntry(
                _id=reply_dicts[0]["_id"],
                board_id=reply_dicts[0]["board_id"],
                user_id=reply_dicts[0]["user_id"],
                comment=reply_dicts[0]["comment"],
                reply=str(reply_dicts[0]["reply"]),
                timestamp=reply_dicts[0]["timestamp"],
                site=reply_dicts[0]["site"]
            )
        except Exception as e:
            logger.error(f"Error adding reply to comment {parents_comment} on board {board_id}: {e}")
            raise e
