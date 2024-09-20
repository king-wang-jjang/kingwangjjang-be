# app/count_controller.py
from datetime import datetime
from typing import List
from typing import Optional
import strawberry
from app.services.count.likes import add_likes
from app.services.count.views import add_views
from app.utils.loghandler import setup_logger

logger = setup_logger()


@strawberry.type
class BoardLikes:
    """ """

    board_id: str
    site: str
    NOWLIKE: int


@strawberry.type
class BoardViews:
    """ """

    board_id: str
    site: str
    NOWVIEW: int


@strawberry.type
class Mutation:
    """ """

    @strawberry.field
    def likes_add(self, board_id: str, site: str) -> BoardLikes:
        """

        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:

        """
        return BoardLikes(board_id=board_id, site=site, NOWLIKE=add_likes(board_id, site))

    @strawberry.field
    def views_add(self, board_id: str, site: str) -> BoardViews:
        """

        :param board_id: str:
        :param site: str:
        :param board_id: str:
        :param site: str:

        """
        return BoardViews(board_id=board_id, site=site, NOWVIEW=add_views(board_id, site))
