# app/count_controller.py
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

import strawberry
from strawberry.types import Info

from app.services.board_comment.add import board_comment_add
from app.celery.types import AddTaskTypes
from app.celery.types import TaskStatusType


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
class Comment:
    """ """

    board_id: str
    site: str
    Comments: List[Dict]


@strawberry.type
class Query:
    """ """

    @strawberry.field
    def hellos(self) -> str:
        """ """
        return "Hello, World!"


@strawberry.type
class Mutation:
    """ """

    @strawberry.mutation
    def comment(self, board_id: str, site: str, userid: str, comment: str) -> Comment:
        """

        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:
        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:
        :param board_id: str:
        :param site: str:
        :param userid: str:
        :param comment: str:

        """

        return Comment(
            board_id=board_id,
            site=site,
            comments=board_comment_add(board_id, site, userid, comment),
        )

    # @strawberry.mutation
    # def reply(self, board_id: str, site: str, userid: str,
    #           parents_comment: str, reply: str) -> Reply:
    #     """
    #
    #     :param board_id: str:
    #     :param site: str:
    #     :param userid: str:
    #     :param parents_comment: str:
    #     :param reply: str:
    #
    #     """
    #     task = task_board_reply_add.apply_async(board_id, site, userid,
    #                                             parents_comment, reply)
    #     return AddTaskTypes(task_id=task.id, status="Processing")
    #


schema = strawberry.Schema(query=Query, mutation=Mutation)
