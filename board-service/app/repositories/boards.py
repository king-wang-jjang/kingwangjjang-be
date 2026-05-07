import logging

from sqlalchemy import desc, inspect, select, text

from app.db.models import Board, BoardLike
from app.db.postgres import Base, get_engine, get_session_factory
from app.utils.constants import DEFAULT_GPT_ANSWER
from app.utils.llm import LLM, LLMError


logger = logging.getLogger("board-service")


class BoardRepository:
    def __init__(self):
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        self._ensure_board_columns(engine)

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

    def analyze_board(self, board_id: str, analyzer: LLM | None = None) -> dict | None:
        analyzer = analyzer or LLM()

        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None
            if self._has_stored_analysis(board):
                return {
                    "board_id": board.id,
                    "summary": board.gpt_answer,
                    "tags": board.tags or [],
                }

            analysis_text = self._analysis_text(board)
            try:
                analysis = analyzer.analyze(analysis_text)
            except LLMError:
                raise
            except Exception as exc:
                raise LLMError(str(exc)) from exc

            board.gpt_answer = analysis["summary"]
            board.tags = analysis["tags"]
            session.commit()
            session.refresh(board)

            return {
                "board_id": board.id,
                "summary": board.gpt_answer,
                "tags": board.tags or [],
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
            "tags": board.tags or [],
            "created_at": board.created_at.isoformat().replace("+00:00", "Z"),
            "thumbnail": board.thumbnail,
            "comment_count": int(board.comment_count or 0),
            "like_count": int(board.like_count or 0),
        }

    @staticmethod
    def _analysis_text(board: Board) -> str:
        parts = [board.title]
        contents = board.contents
        if isinstance(contents, str):
            parts.append(contents)
        elif isinstance(contents, list):
            parts.extend(str(item) for item in contents if item is not None)
        elif isinstance(contents, dict):
            parts.extend(str(value) for value in contents.values() if value is not None)

        return "\n".join(part for part in parts if part)

    @staticmethod
    def _has_stored_analysis(board: Board) -> bool:
        summary = board.gpt_answer.strip() if isinstance(board.gpt_answer, str) else ""
        return bool(summary and summary != DEFAULT_GPT_ANSWER)

    @staticmethod
    def _ensure_board_columns(engine) -> None:
        inspector = inspect(engine)
        if not inspector.has_table("boards"):
            return

        existing_columns = {column["name"] for column in inspector.get_columns("boards")}
        if "tags" in existing_columns:
            return

        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE boards ADD COLUMN tags JSON"))
        logger.info("Added missing boards.tags column")
