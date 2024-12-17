from typing import Optional
import strawberry
from app.services.count.likes import add_likes
from app.services.count.views import add_views
from app.utils.loghandler import setup_logger

# Logger 설정
logger = setup_logger()

@strawberry.type
class BoardLikes:
    """ 게시글 좋아요 수를 나타내는 타입 """
    board_id: str
    site: str
    NOWLIKE: int

@strawberry.type
class BoardViews:
    """ 게시글 조회수 수를 나타내는 타입 """
    board_id: str
    site: str
    NOWVIEW: int

@strawberry.type
class Mutation:
    """ 좋아요와 조회수를 추가하는 Mutation 클래스 """

    @strawberry.field
    def likes_add(self, board_id: str, site: str) -> BoardLikes:
        """
        게시글에 좋아요 수를 추가하는 필드

        :param board_id: 게시글 ID
        :param site: 사이트 이름
        :return: 좋아요가 추가된 BoardLikes 객체
        """
        try:
            now_likes = add_likes(board_id, site)
            logger.info(f"Likes added to board {board_id} on site {site}. Current likes: {now_likes}")
            return BoardLikes(board_id=board_id, site=site, NOWLIKE=now_likes)
        except Exception as e:
            logger.error(f"Error adding likes to board {board_id} on site {site}: {e}")
            raise e

    @strawberry.field
    def views_add(self, board_id: str, site: str) -> BoardViews:
        """
        게시글에 조회수를 추가하는 필드

        :param board_id: 게시글 ID
        :param site: 사이트 이름
        :return: 조회수가 추가된 BoardViews 객체
        """
        try:
            now_views = add_views(board_id, site)
            logger.info(f"Views added to board {board_id} on site {site}. Current views: {now_views}")
            return BoardViews(board_id=board_id, site=site, NOWVIEW=now_views)
        except Exception as e:
            logger.error(f"Error adding views to board {board_id} on site {site}: {e}")
            raise e
