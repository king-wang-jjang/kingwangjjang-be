import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, inspect, nullslast, select, text

from app.db.models import Board, BoardLike
from app.db.postgres import Base, get_engine, get_session_factory
from app.utils.constants import DEFAULT_GPT_ANSWER
from app.utils.crawled_content import extract_llm_text, normalize_contents
from app.utils.llm import LLM, LLMError


logger = logging.getLogger("board-service")


class BoardRepository:
    ANALYSIS_PENDING = "pending"
    ANALYSIS_PROCESSING = "processing"
    ANALYSIS_DONE = "done"
    ANALYSIS_FAILED = "failed"
    USER_REQUEST_PRIORITY = 100
    DEFAULT_MAX_RETRY_COUNT = 2
    PROCESSING_STALE_AFTER = timedelta(minutes=10)

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

    def get_analysis_status(self, board_id: str) -> dict | None:
        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            if self._has_stored_analysis(board):
                return {
                    "board_id": board.id,
                    "summary": board.gpt_answer,
                    "tags": board.tags or [],
                    "is_complete": True,
                }

            return {
                "board_id": board.id,
                "summary": None,
                "tags": board.tags or [],
                "is_complete": False,
            }

    def analyze_board(self, board_id: str, analyzer: LLM | None = None) -> dict | None:
        analyzer = analyzer or LLM()

        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None
            if self._has_stored_analysis(board):
                if board.analysis_status != self.ANALYSIS_DONE:
                    board.analysis_status = self.ANALYSIS_DONE
                    board.analysis_error = None
                    board.analysis_updated_at = self._now()
                    session.commit()
                    session.refresh(board)
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
            board.analysis_status = self.ANALYSIS_DONE
            board.analysis_error = None
            board.analysis_updated_at = self._now()
            session.commit()
            session.refresh(board)

            return {
                "board_id": board.id,
                "summary": board.gpt_answer,
                "tags": board.tags or [],
            }

    def request_analysis(self, board_id: str, priority: int = USER_REQUEST_PRIORITY) -> dict | None:
        now = self._now()
        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            if self._has_stored_analysis(board):
                board.analysis_status = self.ANALYSIS_DONE
                board.analysis_error = None
                board.analysis_updated_at = now
            else:
                if board.analysis_status in {self.ANALYSIS_FAILED, None}:
                    board.analysis_status = self.ANALYSIS_PENDING
                elif board.analysis_status not in {self.ANALYSIS_PENDING, self.ANALYSIS_PROCESSING}:
                    board.analysis_status = self.ANALYSIS_PENDING

                board.analysis_priority = max(int(board.analysis_priority or 0), priority)
                board.analysis_requested_at = now
                board.analysis_updated_at = now

            session.commit()
            session.refresh(board)
            return self._analysis_to_dict(board)

    def get_analysis(self, board_id: str) -> dict | None:
        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            if self._has_stored_analysis(board) and board.analysis_status != self.ANALYSIS_DONE:
                board.analysis_status = self.ANALYSIS_DONE
                board.analysis_error = None
                board.analysis_updated_at = self._now()
                session.commit()
                session.refresh(board)

            return self._analysis_to_dict(board)

    def process_next_analysis_job(
        self,
        analyzer: LLM | None = None,
        max_retry_count: int = DEFAULT_MAX_RETRY_COUNT,
    ) -> dict | None:
        analyzer = analyzer or LLM()
        board_id = self._claim_next_analysis_job(max_retry_count=max_retry_count)
        if board_id is None:
            return None

        try:
            result = self.analyze_board(board_id, analyzer=analyzer)
            if result is None:
                return None
            return {**result, "status": self.ANALYSIS_DONE}
        except LLMError as exc:
            return self._record_analysis_failure(
                board_id,
                error=str(exc),
                max_retry_count=max_retry_count,
            )

    def _claim_next_analysis_job(self, max_retry_count: int) -> str | None:
        now = self._now()
        stale_cutoff = now - self.PROCESSING_STALE_AFTER

        with get_session_factory()() as session:
            stale_boards = session.scalars(
                select(Board).where(
                    Board.analysis_status == self.ANALYSIS_PROCESSING,
                    Board.analysis_started_at.is_not(None),
                    Board.analysis_started_at < stale_cutoff,
                )
            ).all()
            for board in stale_boards:
                board.analysis_status = self.ANALYSIS_PENDING
                board.analysis_error = "stale processing job recovered"
                board.analysis_updated_at = now

            stmt = (
                select(Board)
                .where(
                    Board.analysis_status == self.ANALYSIS_PENDING,
                    Board.analysis_retry_count < max_retry_count,
                )
                .order_by(
                    desc(Board.analysis_priority),
                    nullslast(desc(Board.analysis_requested_at)),
                    desc(Board.created_at),
                )
                .limit(1)
            )
            if get_engine().dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)

            board = session.scalars(stmt).first()
            if board is None:
                session.commit()
                return None

            if self._has_stored_analysis(board):
                board.analysis_status = self.ANALYSIS_DONE
                board.analysis_error = None
                board.analysis_updated_at = now
                session.commit()
                return board.id

            board.analysis_status = self.ANALYSIS_PROCESSING
            board.analysis_started_at = now
            board.analysis_updated_at = now
            session.commit()
            return board.id

    def _record_analysis_failure(self, board_id: str, error: str, max_retry_count: int) -> dict | None:
        now = self._now()
        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            retry_count = int(board.analysis_retry_count or 0) + 1
            board.analysis_retry_count = retry_count
            board.analysis_error = error[:1000]
            board.analysis_started_at = None
            board.analysis_updated_at = now
            if retry_count >= max_retry_count:
                board.analysis_status = self.ANALYSIS_FAILED
            else:
                board.analysis_status = self.ANALYSIS_PENDING
                board.analysis_priority = max(int(board.analysis_priority or 0) - 1, 0)

            session.commit()
            session.refresh(board)
            return self._analysis_to_dict(board)

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

    def _to_dict(self, board: Board) -> dict:
        return {
            "id": board.id,
            "category": board.category,
            "no": board.no,
            "site": board.site,
            "title": board.title,
            "url": board.url,
            "contents": normalize_contents(board.contents),
            "gpt_answer": board.gpt_answer,
            "tags": board.tags or [],
            "analysis_status": board.analysis_status or self.ANALYSIS_PENDING,
            "analysis_priority": int(board.analysis_priority or 0),
            "analysis_retry_count": int(board.analysis_retry_count or 0),
            "analysis_error": board.analysis_error,
            "analysis_requested_at": self._datetime_to_api(board.analysis_requested_at),
            "analysis_started_at": self._datetime_to_api(board.analysis_started_at),
            "analysis_updated_at": self._datetime_to_api(board.analysis_updated_at),
            "created_at": board.created_at.isoformat().replace("+00:00", "Z"),
            "thumbnail": board.thumbnail,
            "comment_count": int(board.comment_count or 0),
            "like_count": int(board.like_count or 0),
        }

    @staticmethod
    def _analysis_text(board: Board) -> str:
        return extract_llm_text(board.title, board.contents)

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
        column_definitions = {
            "tags": "JSON",
            "analysis_status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
            "analysis_priority": "INTEGER NOT NULL DEFAULT 0",
            "analysis_requested_at": "TIMESTAMP",
            "analysis_started_at": "TIMESTAMP",
            "analysis_updated_at": "TIMESTAMP",
            "analysis_retry_count": "INTEGER NOT NULL DEFAULT 0",
            "analysis_error": "TEXT",
        }
        missing_columns = {
            column_name: definition
            for column_name, definition in column_definitions.items()
            if column_name not in existing_columns
        }
        if not missing_columns:
            return

        with engine.begin() as connection:
            for column_name, definition in missing_columns.items():
                connection.execute(text(f"ALTER TABLE boards ADD COLUMN {column_name} {definition}"))
                logger.info("Added missing boards.%s column", column_name)

    def _analysis_to_dict(self, board: Board) -> dict:
        summary = board.gpt_answer if self._has_stored_analysis(board) else None
        return {
            "board_id": board.id,
            "status": board.analysis_status or self.ANALYSIS_PENDING,
            "summary": summary,
            "tags": board.tags or [],
            "retry_count": int(board.analysis_retry_count or 0),
            "error": board.analysis_error,
            "requested_at": self._datetime_to_api(board.analysis_requested_at),
            "started_at": self._datetime_to_api(board.analysis_started_at),
            "updated_at": self._datetime_to_api(board.analysis_updated_at),
        }

    @staticmethod
    def _datetime_to_api(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
