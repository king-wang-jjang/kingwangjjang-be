from sqlalchemy import desc, select

from app.db.models import Board, BoardLike
from app.db.postgres import Base, get_engine, get_session_factory


class BoardRepository:
    def __init__(self):
        Base.metadata.create_all(bind=get_engine())

    def list_realtime(self, index: int, limit: int) -> list[dict]:
        return self._list_boards(index=index, limit=limit, daily=False)

    def list_daily(self, index: int, limit: int) -> list[dict]:
        return self._list_boards(index=index, limit=limit, daily=True)

    def add_like(self, board_id: str, user_id: str) -> dict | None:
        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            like = session.scalar(
                select(BoardLike).where(
                    BoardLike.board_id == board_id,
                    BoardLike.user_id == user_id,
                )
            )
            if like is None:
                session.add(BoardLike(board_id=board_id, user_id=user_id))
                board.like_count = int(board.like_count or 0) + 1
                session.commit()
                session.refresh(board)

            return {
                "board_id": board.id,
                "site": board.site,
                "like_count": int(board.like_count or 0),
            }

    def _list_boards(self, index: int, limit: int, daily: bool) -> list[dict]:
        offset = max(index, 0) * max(limit, 1)
        ordering = desc(Board.like_count) if daily else desc(Board.created_at)

        with get_session_factory()() as session:
            boards = session.scalars(
                select(Board)
                .order_by(ordering, desc(Board.created_at))
                .offset(offset)
                .limit(limit)
            ).all()

            return [self._to_dict(board) for board in boards]

    @staticmethod
    def _to_dict(board: Board) -> dict:
        return {
            "id": board.id,
            "category": board.category,
            "no": board.no,
            "site": board.site,
            "title": board.title,
            "url": board.url,
            "contents": board.contents,
            "gpt_answer": board.gpt_answer,
            "created_at": board.created_at.isoformat().replace("+00:00", "Z"),
            "thumbnail": board.thumbnail,
            "comment_count": int(board.comment_count or 0),
            "like_count": int(board.like_count or 0),
        }
