import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import exp, isfinite

from sqlalchemy import String, cast, delete, desc, func, inspect, nullslast, or_, select, text

from app.db.models import Board, BoardLike, BoardMetricSnapshot, DailyTop10Snapshot
from app.db.postgres import Base, get_engine, get_session_factory
from app.services.popularity import (
    DAILY_DECAY_HOURS,
    HOT_DECAY_HOURS,
    PopularityMetrics,
    calculate_popularity_scores,
)
from app.services.vision_text import VisionTextClient, resolve_media_path
from app.utils.constants import DEFAULT_GPT_ANSWER
from app.utils.crawled_content import extract_llm_text, normalize_contents
from app.utils.llm import LLM, LLMError


logger = logging.getLogger("board-service")
SNAPSHOT_RETENTION_DAYS = 7
SNAPSHOT_CLEANUP_INTERVAL = timedelta(hours=1)
RECENT_CRAWL_WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class BoardListFilters:
    sites: tuple[str, ...] = ()
    category: str | None = None
    tag: str | None = None
    query: str | None = None
    has_thumbnail: bool | None = None

    @classmethod
    def from_values(
        cls,
        *,
        sites: list[str] | None = None,
        category: str | None = None,
        tag: str | None = None,
        query: str | None = None,
        has_thumbnail: bool | None = None,
    ) -> "BoardListFilters":
        return cls(
            sites=tuple(_split_filter_values(sites or [])),
            category=_clean_filter_value(category),
            tag=_clean_filter_value(tag),
            query=_clean_filter_value(query),
            has_thumbnail=has_thumbnail,
        )


class BoardRepository:
    ANALYSIS_PENDING = "pending"
    ANALYSIS_PROCESSING = "processing"
    ANALYSIS_DONE = "done"
    ANALYSIS_FAILED = "failed"
    USER_REQUEST_PRIORITY = 100
    DEFAULT_MAX_RETRY_COUNT = 2
    PROCESSING_STALE_AFTER = timedelta(minutes=10)

    def __init__(self):
        self._last_snapshot_cleanup_at: datetime | None = None
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        self._ensure_board_columns(engine)

    def list_realtime(
        self,
        index: int,
        limit: int,
        filters: BoardListFilters | None = None,
    ) -> list[dict]:
        return self._list_boards(index=index, limit=limit, daily=False, filters=filters)

    def list_daily(
        self,
        index: int,
        limit: int,
        filters: BoardListFilters | None = None,
    ) -> list[dict]:
        return self._list_boards(index=index, limit=limit, daily=True, filters=filters)

    def list_recently_crawled_sites(self, *, as_of: datetime | None = None) -> list[str]:
        reference_time = as_of or self._now()
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        else:
            reference_time = reference_time.astimezone(timezone.utc)
        cutoff = reference_time - RECENT_CRAWL_WINDOW

        stmt = (
            select(Board.site)
            .join(BoardMetricSnapshot, BoardMetricSnapshot.board_id == Board.id)
            .where(
                BoardMetricSnapshot.captured_at >= cutoff,
                BoardMetricSnapshot.captured_at <= reference_time,
                BoardMetricSnapshot.crawl_status == "success",
            )
            .distinct()
            .order_by(Board.site)
        )
        with get_session_factory()() as session:
            return [
                site
                for site in session.scalars(stmt).all()
                if site
            ]

    def list_daily_history_dates(self, limit: int = 30) -> list[date]:
        page_size = max(1, min(limit, 365))
        with get_session_factory()() as session:
            return list(
                session.scalars(
                    select(DailyTop10Snapshot.snapshot_date)
                    .distinct()
                    .order_by(desc(DailyTop10Snapshot.snapshot_date))
                    .limit(page_size)
                ).all()
            )

    def list_daily_history(self, snapshot_date: date, limit: int = 10) -> list[dict]:
        page_size = max(1, min(limit, 100))
        stmt = (
            select(Board, DailyTop10Snapshot.daily_score)
            .join(DailyTop10Snapshot, DailyTop10Snapshot.board_id == Board.id)
            .where(DailyTop10Snapshot.snapshot_date == snapshot_date)
            .order_by(DailyTop10Snapshot.rank)
            .limit(page_size)
        )

        with get_session_factory()() as session:
            result = []
            for board, snapshot_daily_score in session.execute(stmt).all():
                board_data = self._to_dict(board)
                board_data["daily_score"] = snapshot_daily_score
                result.append(board_data)
            return result

    def record_metric_snapshot(
        self,
        board_id: str,
        *,
        comment_count: int,
        like_count: int,
        view_count: int | None = None,
        source_rank: int | None = None,
        captured_at: datetime | None = None,
        crawl_status: str = "success",
        crawl_error: str | None = None,
    ) -> dict | None:
        captured_at = captured_at or self._now()
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)

        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            if (
                self._last_snapshot_cleanup_at is None
                or captured_at - self._last_snapshot_cleanup_at
                >= SNAPSHOT_CLEANUP_INTERVAL
            ):
                session.execute(
                    delete(BoardMetricSnapshot).where(
                        BoardMetricSnapshot.captured_at
                        < captured_at - timedelta(days=SNAPSHOT_RETENTION_DAYS),
                    )
                )
                self._last_snapshot_cleanup_at = captured_at
            previous_snapshots = session.scalars(
                select(BoardMetricSnapshot)
                .where(BoardMetricSnapshot.board_id == board_id)
                .order_by(desc(BoardMetricSnapshot.captured_at))
                .limit(2)
            ).all()
            previous_snapshot = previous_snapshots[0] if previous_snapshots else None
            previous_previous_snapshot = previous_snapshots[1] if len(previous_snapshots) > 1 else None

            scores = calculate_popularity_scores(
                PopularityMetrics(
                    site=board.site,
                    created_at=board.created_at,
                    captured_at=captured_at,
                    comment_count=comment_count,
                    like_count=like_count,
                    view_count=view_count,
                    source_rank=source_rank,
                    llm_engagement_score=board.llm_engagement_score,
                    previous_comment_count=getattr(previous_snapshot, "comment_count", None),
                    previous_like_count=getattr(previous_snapshot, "like_count", None),
                    previous_view_count=getattr(previous_snapshot, "view_count", None),
                    previous_captured_at=getattr(previous_snapshot, "captured_at", None),
                    previous_delta_comments=self._snapshot_delta(
                        previous_snapshot,
                        previous_previous_snapshot,
                        "comment_count",
                    ),
                    previous_delta_likes=self._snapshot_delta(
                        previous_snapshot,
                        previous_previous_snapshot,
                        "like_count",
                    ),
                    previous_delta_views=self._snapshot_delta(
                        previous_snapshot,
                        previous_previous_snapshot,
                        "view_count",
                    ),
                    previous_interval_minutes=self._snapshot_interval_minutes(
                        previous_snapshot,
                        previous_previous_snapshot,
                    ),
                )
            )

            session.add(
                BoardMetricSnapshot(
                    board_id=board_id,
                    captured_at=captured_at,
                    comment_count=max(int(comment_count or 0), 0),
                    like_count=max(int(like_count or 0), 0),
                    view_count=view_count,
                    source_rank=source_rank,
                    crawl_status=crawl_status,
                    crawl_error=crawl_error,
                )
            )
            board.native_comment_count = max(int(comment_count or 0), 0)
            board.native_like_count = max(int(like_count or 0), 0)
            board.native_view_count = view_count
            board.source_rank = source_rank
            board.metrics_crawled_at = captured_at
            board.hot_score = scores.hot_score
            board.daily_score = scores.daily_score
            board.score_breakdown = scores.breakdown
            board.score_updated_at = captured_at

            session.commit()
            session.refresh(board)
            return self._to_dict(board)

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

            if self._has_complete_analysis(board):
                return {
                    "board_id": board.id,
                    "summary": board.gpt_answer,
                    "tags": board.tags or [],
                    "llm_engagement_score": board.llm_engagement_score,
                    "llm_engagement_reason": board.llm_engagement_reason,
                    "is_complete": True,
                }

            return {
                "board_id": board.id,
                "summary": None,
                "tags": board.tags or [],
                "llm_engagement_score": board.llm_engagement_score,
                "llm_engagement_reason": board.llm_engagement_reason,
                "is_complete": False,
            }

    def analyze_board(self, board_id: str, analyzer: LLM | None = None) -> dict | None:
        analyzer = analyzer or LLM()

        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None
            if self._has_complete_analysis(board):
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
                    "llm_engagement_score": board.llm_engagement_score,
                    "llm_engagement_reason": board.llm_engagement_reason,
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
            if "llm_engagement_score" in analysis:
                board.llm_engagement_score = self._optional_llm_score(
                    analysis.get("llm_engagement_score")
                )
            if "llm_engagement_reason" in analysis:
                board.llm_engagement_reason = self._optional_llm_reason(
                    analysis.get("llm_engagement_reason")
                )
            board.analysis_status = self.ANALYSIS_DONE
            board.analysis_error = None
            board.analysis_updated_at = self._now()
            self._recalculate_popularity_scores(session, board)
            session.commit()
            session.refresh(board)

            return {
                "board_id": board.id,
                "summary": board.gpt_answer,
                "tags": board.tags or [],
                "llm_engagement_score": board.llm_engagement_score,
                "llm_engagement_reason": board.llm_engagement_reason,
            }

    def request_analysis(self, board_id: str, priority: int = USER_REQUEST_PRIORITY) -> dict | None:
        now = self._now()
        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            if self._has_complete_analysis(board):
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

            if self._has_complete_analysis(board) and board.analysis_status != self.ANALYSIS_DONE:
                board.analysis_status = self.ANALYSIS_DONE
                board.analysis_error = None
                board.analysis_updated_at = self._now()
                session.commit()
                session.refresh(board)

            return self._analysis_to_dict(board)

    def extract_image_text(
        self,
        board_id: str,
        *,
        image_index: int = 0,
        extractor: VisionTextClient | None = None,
        media_root=None,
        prompt: str | None = None,
    ) -> dict | None:
        extractor = extractor or VisionTextClient()

        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None

            image_block = self._image_block_at(board.contents, image_index)
            if image_block is None:
                raise ValueError("Image not found")

            media_path = image_block.get("media_path")
            if not media_path:
                raise ValueError("Image media path is missing")

            image_path = resolve_media_path(media_path, media_root=media_root)
            text = extractor.extract_text(image_path, prompt=prompt)

            return {
                "board_id": board.id,
                "image_index": image_index,
                "media_path": media_path,
                "text": text,
            }

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

            if self._has_complete_analysis(board):
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

    def _recalculate_popularity_scores(self, session, board: Board) -> None:
        """Re-score a board after LLM analysis without creating a metric snapshot."""
        snapshots = session.scalars(
            select(BoardMetricSnapshot)
            .where(BoardMetricSnapshot.board_id == board.id)
            .order_by(desc(BoardMetricSnapshot.captured_at))
            .limit(3)
        ).all()
        current_snapshot = snapshots[0] if snapshots else None
        previous_snapshot = snapshots[1] if len(snapshots) > 1 else None
        previous_previous_snapshot = snapshots[2] if len(snapshots) > 2 else None
        captured_at = (
            current_snapshot.captured_at if current_snapshot is not None else self._now()
        )

        scores = calculate_popularity_scores(
            PopularityMetrics(
                site=board.site,
                created_at=board.created_at,
                captured_at=captured_at,
                comment_count=(
                    current_snapshot.comment_count
                    if current_snapshot is not None
                    else int(board.native_comment_count or 0)
                ),
                like_count=(
                    current_snapshot.like_count
                    if current_snapshot is not None
                    else int(board.native_like_count or 0)
                ),
                view_count=(
                    current_snapshot.view_count
                    if current_snapshot is not None
                    else board.native_view_count
                ),
                source_rank=(
                    current_snapshot.source_rank
                    if current_snapshot is not None
                    else board.source_rank
                ),
                llm_engagement_score=board.llm_engagement_score,
                previous_comment_count=getattr(previous_snapshot, "comment_count", None),
                previous_like_count=getattr(previous_snapshot, "like_count", None),
                previous_view_count=getattr(previous_snapshot, "view_count", None),
                previous_captured_at=getattr(previous_snapshot, "captured_at", None),
                previous_delta_comments=self._snapshot_delta(
                    previous_snapshot,
                    previous_previous_snapshot,
                    "comment_count",
                ),
                previous_delta_likes=self._snapshot_delta(
                    previous_snapshot,
                    previous_previous_snapshot,
                    "like_count",
                ),
                previous_delta_views=self._snapshot_delta(
                    previous_snapshot,
                    previous_previous_snapshot,
                    "view_count",
                ),
                previous_interval_minutes=self._snapshot_interval_minutes(
                    previous_snapshot,
                    previous_previous_snapshot,
                ),
            )
        )
        board.hot_score = scores.hot_score
        board.daily_score = scores.daily_score
        board.score_breakdown = scores.breakdown
        board.score_updated_at = captured_at

    @staticmethod
    def _optional_llm_score(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(numeric_value):
            return None
        return max(0, min(int(round(numeric_value)), 100))

    @staticmethod
    def _optional_llm_reason(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        reason = value.strip()
        return reason[:240] or None

    def _list_boards(
        self,
        index: int,
        limit: int,
        daily: bool,
        filters: BoardListFilters | None = None,
    ) -> list[dict]:
        page_size = max(limit, 1)
        offset = max(index, 0) * page_size
        ordering = desc(self._effective_score_expression(daily=daily))
        stmt = self._apply_list_filters(select(Board), filters or BoardListFilters())
        secondary_ordering = desc(Board.like_count) if daily else desc(Board.created_at)
        score_as_of = self._now()

        with get_session_factory()() as session:
            boards = session.scalars(
                stmt.order_by(ordering, secondary_ordering, desc(Board.created_at))
                .offset(offset)
                .limit(page_size)
            ).all()

            return [self._to_dict(board, score_as_of=score_as_of) for board in boards]

    @staticmethod
    def _effective_score_expression(*, daily: bool):
        score_column = Board.daily_score if daily else Board.hot_score
        decay_hours = DAILY_DECAY_HOURS if daily else HOT_DECAY_HOURS
        updated_at = func.coalesce(Board.score_updated_at, Board.created_at)
        engine = get_engine()
        if engine.dialect.name == "postgresql":
            elapsed_hours = func.greatest(
                func.extract("epoch", func.current_timestamp() - updated_at) / 3600.0,
                0.0,
            )
        else:
            elapsed_hours = func.max(
                (func.julianday(func.current_timestamp()) - func.julianday(updated_at)) * 24.0,
                0.0,
            )
        return func.coalesce(score_column, 0.0) * func.exp(-elapsed_hours / decay_hours)

    @staticmethod
    def _apply_list_filters(stmt, filters: BoardListFilters):
        if filters.sites:
            stmt = stmt.where(Board.site.in_(filters.sites))

        if filters.category:
            stmt = stmt.where(Board.category == filters.category)

        if filters.tag:
            stmt = stmt.where(cast(Board.tags, String).ilike(f'%"{filters.tag}"%'))

        if filters.query:
            search_pattern = f"%{filters.query}%"
            stmt = stmt.where(
                or_(Board.title.ilike(search_pattern), Board.url.ilike(search_pattern))
            )

        if filters.has_thumbnail is True:
            stmt = stmt.where(Board.thumbnail.is_not(None), Board.thumbnail != "")
        elif filters.has_thumbnail is False:
            stmt = stmt.where(or_(Board.thumbnail.is_(None), Board.thumbnail == ""))

        return stmt

    def _to_dict(self, board: Board, score_as_of: datetime | None = None) -> dict:
        hot_score = board.hot_score
        daily_score = board.daily_score
        if score_as_of is not None:
            updated_at = board.score_updated_at or board.created_at
            hot_score = self._effective_score_value(
                hot_score,
                updated_at,
                score_as_of,
                HOT_DECAY_HOURS,
            )
            daily_score = self._effective_score_value(
                daily_score,
                updated_at,
                score_as_of,
                DAILY_DECAY_HOURS,
            )
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
            "llm_engagement_score": board.llm_engagement_score,
            "llm_engagement_reason": board.llm_engagement_reason,
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
            "native_comment_count": board.native_comment_count,
            "native_like_count": board.native_like_count,
            "native_view_count": board.native_view_count,
            "source_rank": board.source_rank,
            "hot_score": hot_score,
            "daily_score": daily_score,
            "score_breakdown": board.score_breakdown or {},
            "metrics_crawled_at": self._datetime_to_api(board.metrics_crawled_at),
            "score_updated_at": self._datetime_to_api(board.score_updated_at),
        }

    @staticmethod
    def _effective_score_value(
        score: float | None,
        updated_at: datetime,
        as_of: datetime,
        decay_hours: float,
    ) -> float:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)
        elapsed_hours = max((as_of - updated_at).total_seconds() / 3600, 0.0)
        return float(score or 0.0) * exp(-elapsed_hours / decay_hours)

    @staticmethod
    def _analysis_text(board: Board) -> str:
        return extract_llm_text(board.title, board.contents)

    @staticmethod
    def _image_block_at(contents: object, image_index: int) -> dict | None:
        if image_index < 0:
            return None

        images = [
            block
            for block in normalize_contents(contents)
            if block.get("type") == "image"
        ]
        if image_index >= len(images):
            return None
        return images[image_index]

    @staticmethod
    def _has_stored_analysis(board: Board) -> bool:
        summary = board.gpt_answer.strip() if isinstance(board.gpt_answer, str) else ""
        return bool(summary and summary != DEFAULT_GPT_ANSWER)

    @classmethod
    def _has_complete_analysis(cls, board: Board) -> bool:
        return cls._has_stored_analysis(board) and board.llm_engagement_score is not None

    @staticmethod
    def _ensure_board_columns(engine) -> None:
        inspector = inspect(engine)
        if not inspector.has_table("boards"):
            return

        existing_columns = {column["name"] for column in inspector.get_columns("boards")}
        column_definitions = {
            "tags": "JSON",
            "llm_engagement_score": "INTEGER",
            "llm_engagement_reason": "TEXT",
            "analysis_status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
            "analysis_priority": "INTEGER NOT NULL DEFAULT 0",
            "analysis_requested_at": "TIMESTAMP",
            "analysis_started_at": "TIMESTAMP",
            "analysis_updated_at": "TIMESTAMP",
            "analysis_retry_count": "INTEGER NOT NULL DEFAULT 0",
            "analysis_error": "TEXT",
            "native_comment_count": "INTEGER",
            "native_like_count": "INTEGER",
            "native_view_count": "INTEGER",
            "source_rank": "INTEGER",
            "metrics_crawled_at": "TIMESTAMP",
            "next_metrics_crawl_at": "TIMESTAMP",
            "hot_score": "FLOAT",
            "daily_score": "FLOAT",
            "score_updated_at": "TIMESTAMP",
            "score_breakdown": "JSON",
        }
        missing_columns = {
            column_name: definition
            for column_name, definition in column_definitions.items()
            if column_name not in existing_columns
        }
        existing_index_names = {
            index["name"]
            for index in inspector.get_indexes("board_metric_snapshots")
        }
        index_definitions = {
            "ix_board_metric_snapshots_board_captured_at": (
                "ON board_metric_snapshots (board_id, captured_at)"
            ),
            "ix_board_metric_snapshots_captured_at": (
                "ON board_metric_snapshots (captured_at)"
            ),
        }
        missing_indexes = {
            name: definition
            for name, definition in index_definitions.items()
            if name not in existing_index_names
        }
        if not missing_columns and not missing_indexes:
            return

        with engine.begin() as connection:
            for column_name, definition in missing_columns.items():
                if_not_exists = "IF NOT EXISTS " if engine.dialect.name == "postgresql" else ""
                connection.execute(
                    text(
                        f"ALTER TABLE boards ADD COLUMN {if_not_exists}{column_name} {definition}"
                    )
                )
                logger.info("Added missing boards.%s column", column_name)
            for index_name, definition in missing_indexes.items():
                connection.execute(
                    text(f"CREATE INDEX IF NOT EXISTS {index_name} {definition}")
                )
            if "llm_engagement_score" in missing_columns:
                connection.execute(
                    text(
                        "UPDATE boards SET analysis_status = 'pending', "
                        "analysis_retry_count = 0 "
                        "WHERE llm_engagement_score IS NULL "
                        "AND gpt_answer IS NOT NULL AND gpt_answer <> :default_answer"
                    ),
                    {"default_answer": DEFAULT_GPT_ANSWER},
                )

    def _analysis_to_dict(self, board: Board) -> dict:
        summary = board.gpt_answer if self._has_stored_analysis(board) else None
        return {
            "board_id": board.id,
            "status": board.analysis_status or self.ANALYSIS_PENDING,
            "summary": summary,
            "tags": board.tags or [],
            "llm_engagement_score": board.llm_engagement_score,
            "llm_engagement_reason": board.llm_engagement_reason,
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

    @staticmethod
    def _snapshot_delta(
        current: BoardMetricSnapshot | None,
        previous: BoardMetricSnapshot | None,
        attr: str,
    ) -> int:
        if current is None or previous is None:
            return 0
        current_value = getattr(current, attr) or 0
        previous_value = getattr(previous, attr) or 0
        return max(int(current_value) - int(previous_value), 0)

    @staticmethod
    def _snapshot_interval_minutes(
        current: BoardMetricSnapshot | None,
        previous: BoardMetricSnapshot | None,
    ) -> float | None:
        if current is None or previous is None:
            return None
        elapsed_seconds = (current.captured_at - previous.captured_at).total_seconds()
        if elapsed_seconds <= 0:
            return None
        return elapsed_seconds / 60


def _clean_filter_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _split_filter_values(values: list[str]) -> list[str]:
    cleaned_values = []
    for value in values:
        for candidate in str(value).split(","):
            cleaned = candidate.strip()
            if cleaned and cleaned not in cleaned_values:
                cleaned_values.append(cleaned)
    return cleaned_values
