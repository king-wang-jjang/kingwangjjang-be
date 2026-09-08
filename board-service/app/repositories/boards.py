import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import exp, isfinite

from sqlalchemy import JSON, case, cast, delete, desc, func, inspect, nullslast, or_, select, text

from app.db.models import Board, BoardLike, BoardMetricSnapshot, DailyTop10Snapshot
from app.db.postgres import Base, get_engine, get_session_factory
from app.services.popularity import (
    DAILY_DECAY_HOURS,
    HOT_DECAY_HOURS,
    PopularityMetrics,
    calculate_popularity_scores,
)
from app.services.ranking import (
    DAILY_ACTIVE_SITE_HOURS,
    HOT_ACTIVE_SITE_HOURS,
    RankingCandidate,
    balance_site_exposure,
)
from app.services.vision_text import (
    VisionTextClient,
    VisionTextError,
    resolve_media_path,
    validate_image_file,
)
from app.utils.constants import DEFAULT_GPT_ANSWER
from app.utils.crawled_content import (
    analysis_max_input_chars,
    analysis_min_body_chars,
    analysis_min_language_chars,
    analysis_retryable_backoff_seconds,
    analysis_vision_fallback_enabled,
    analysis_vision_max_image_bytes,
    analysis_vision_max_images,
    analysis_vision_max_pixels,
    analysis_vision_prompt,
    extract_llm_text,
    has_sufficient_analysis_body,
    normalize_contents,
)
from app.utils.llm import LLM, LLMError


logger = logging.getLogger("board-service")
SNAPSHOT_RETENTION_DAYS = 7
SNAPSHOT_CLEANUP_INTERVAL = timedelta(hours=1)
RECENT_CRAWL_WINDOW = timedelta(hours=24)
VISION_FALLBACK_UNAVAILABLE_ERROR = (
    "Vision fallback is temporarily unavailable; retry after the vision node recovers"
)
VISION_FALLBACK_REJECTED_ERROR = (
    "Vision fallback request was rejected; check vision node configuration"
)
INSUFFICIENT_ANALYSIS_CONTENT_ERROR = "Board content is too short for reliable analysis"
CRAWLER_CONTENT_REFRESH_REQUIRED_ERROR = (
    "crawled body is insufficient for AI analysis; content refresh required"
)
TERMINAL_ANALYSIS_ERRORS = (
    INSUFFICIENT_ANALYSIS_CONTENT_ERROR,
    CRAWLER_CONTENT_REFRESH_REQUIRED_ERROR,
    VISION_FALLBACK_REJECTED_ERROR,
)


class RetryableAnalysisError(LLMError):
    pass


@dataclass(frozen=True)
class BoardListFilters:
    sites: tuple[str, ...] = ()
    category: str | None = None
    tag: str | None = None
    query: str | None = None
    has_thumbnail: bool | None = None

    @property
    def is_default(self) -> bool:
        return not (
            self.sites
            or self.category
            or self.tag
            or self.query
            or self.has_thumbnail is not None
        )

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
            tag=_clean_tag_value(tag),
            query=_clean_filter_value(query),
            has_thumbnail=has_thumbnail,
        )


class BoardRepository:
    ANALYSIS_PENDING = "pending"
    ANALYSIS_PROCESSING = "processing"
    ANALYSIS_DONE = "done"
    ANALYSIS_FAILED = "failed"
    USER_REQUEST_PRIORITY = 100
    DEFAULT_MAX_RETRY_COUNT = 5
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

    def get_analysis_queue_metrics(self, as_of: datetime | None = None) -> dict:
        """Return queue depth and recent flow without loading board content."""
        now = as_of or self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        stale_cutoff = now - self.PROCESSING_STALE_AFTER

        def count_when(condition):
            return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)

        pending = Board.analysis_status == self.ANALYSIS_PENDING
        processing = Board.analysis_status == self.ANALYSIS_PROCESSING
        done = Board.analysis_status == self.ANALYSIS_DONE
        failed = Board.analysis_status == self.ANALYSIS_FAILED
        ready_pending = pending & or_(
            Board.analysis_requested_at.is_(None),
            Board.analysis_requested_at <= now,
        )
        stale_processing = (
            processing
            & Board.analysis_started_at.is_not(None)
            & (Board.analysis_started_at < stale_cutoff)
        )
        recent_completion = (
            done
            & Board.analysis_updated_at.is_not(None)
            & (Board.analysis_updated_at >= hour_ago)
        )

        with get_session_factory()() as session:
            row = session.execute(
                select(
                    func.count(Board.id),
                    count_when(pending),
                    count_when(ready_pending),
                    count_when(processing),
                    count_when(done),
                    count_when(failed),
                    count_when(stale_processing),
                    func.min(case((pending, Board.created_at), else_=None)),
                    count_when(Board.created_at >= hour_ago),
                    count_when(recent_completion),
                )
            ).one()

        (
            total_count,
            pending_count,
            ready_pending_count,
            processing_count,
            done_count,
            failed_count,
            stale_processing_count,
            oldest_pending_at,
            recent_arrivals,
            recent_completions,
        ) = row

        if oldest_pending_at is not None:
            if oldest_pending_at.tzinfo is None:
                oldest_pending_at = oldest_pending_at.replace(tzinfo=timezone.utc)
            else:
                oldest_pending_at = oldest_pending_at.astimezone(timezone.utc)
            oldest_pending_age_seconds = max(
                0,
                int((now - oldest_pending_at).total_seconds()),
            )
        else:
            oldest_pending_age_seconds = 0

        return {
            "generated_at": now,
            "total_count": int(total_count),
            "pending_count": int(pending_count),
            "ready_pending_count": int(ready_pending_count),
            "deferred_pending_count": max(
                0, int(pending_count) - int(ready_pending_count)
            ),
            "processing_count": int(processing_count),
            "done_count": int(done_count),
            "failed_count": int(failed_count),
            "stale_processing_count": int(stale_processing_count),
            "oldest_pending_at": oldest_pending_at,
            "oldest_pending_age_seconds": oldest_pending_age_seconds,
            "recent_arrivals": int(recent_arrivals),
            "recent_completions": int(recent_completions),
        }

    def get_issue_overview(
        self,
        *,
        window_hours: int = 24,
        limit: int = 16,
        sites: tuple[str, ...] = (),
        as_of: datetime | None = None,
    ) -> dict:
        """Aggregate AI-generated tag momentum without loading board bodies."""
        reference_time = as_of or self._now()
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        else:
            reference_time = reference_time.astimezone(timezone.utc)

        bounded_hours = max(6, min(int(window_hours), 168))
        tag_limit = max(4, min(int(limit), 24))
        window_start = reference_time - timedelta(hours=bounded_hours)
        current_period_start = reference_time - timedelta(hours=bounded_hours / 2)

        stmt = select(
            Board.site,
            Board.tags,
            Board.created_at,
            Board.hot_score,
            Board.score_updated_at,
        ).where(
            Board.created_at >= window_start,
            Board.created_at <= reference_time,
            Board.analysis_status == self.ANALYSIS_DONE,
        )
        if sites:
            stmt = stmt.where(Board.site.in_(sites))

        with get_session_factory()() as session:
            rows = session.execute(stmt).all()

        tag_aggregates: dict[str, dict] = {}
        tag_labels: dict[str, str] = {}
        analyzed_post_count = 0
        for site, tags, created_at, hot_score, score_updated_at in rows:
            normalized_tags: list[tuple[str, str]] = []
            seen_tags: set[str] = set()
            for raw_tag in tags if isinstance(tags, list) else []:
                tag_label = _clean_tag_value(str(raw_tag or ""))
                if not tag_label:
                    continue
                tag_key = tag_label.casefold()
                if tag_key in seen_tags:
                    continue
                seen_tags.add(tag_key)
                tag_labels.setdefault(tag_key, tag_label)
                normalized_tags.append((tag_key, tag_labels[tag_key]))

            if not normalized_tags:
                continue

            analyzed_post_count += 1
            site_name = str(site or "").strip() or "unknown"
            created_at = self._as_utc(created_at)
            score_updated_at = self._as_utc(score_updated_at or created_at)
            raw_hot_score = float(hot_score or 0.0)
            if not isfinite(raw_hot_score):
                raw_hot_score = 0.0
            effective_hot_score = self._effective_score_value(
                max(raw_hot_score, 0.0),
                score_updated_at,
                reference_time,
                HOT_DECAY_HOURS,
            )

            for tag_key, tag_label in normalized_tags:
                aggregate = tag_aggregates.setdefault(
                    tag_key,
                    {
                        "tag": tag_label,
                        "post_count": 0,
                        "current_posts": 0,
                        "previous_posts": 0,
                        "impact_score": 0.0,
                        "sites": Counter(),
                        "related_tags": Counter(),
                    },
                )
                aggregate["post_count"] += 1
                aggregate["impact_score"] += 1.0 + effective_hot_score
                if created_at >= current_period_start:
                    aggregate["current_posts"] += 1
                else:
                    aggregate["previous_posts"] += 1
                aggregate["sites"][site_name] += 1
                for related_key, _related_label in normalized_tags:
                    if related_key != tag_key:
                        aggregate["related_tags"][related_key] += 1

        total_impact = sum(item["impact_score"] for item in tag_aggregates.values())
        ranked_tags = sorted(
            tag_aggregates.values(),
            key=lambda item: (
                -item["impact_score"],
                -item["post_count"],
                item["tag"].casefold(),
            ),
        )[:tag_limit]

        result_tags = []
        for item in ranked_tags:
            current_posts = item["current_posts"]
            previous_posts = item["previous_posts"]
            momentum_percent = ((current_posts + 1) / (previous_posts + 1) - 1) * 100
            top_sites = sorted(
                item["sites"].items(),
                key=lambda pair: (-pair[1], pair[0]),
            )[:3]
            related_tags = sorted(
                item["related_tags"].items(),
                key=lambda pair: (-pair[1], pair[0]),
            )[:3]
            result_tags.append(
                {
                    "tag": item["tag"],
                    "post_count": item["post_count"],
                    "current_posts": current_posts,
                    "previous_posts": previous_posts,
                    "impact_score": round(item["impact_score"], 4),
                    "share": round(item["impact_score"] / total_impact, 6)
                    if total_impact
                    else 0.0,
                    "momentum_percent": round(momentum_percent, 1),
                    "top_sites": [
                        {"site": site_name, "post_count": count}
                        for site_name, count in top_sites
                    ],
                    "related_tags": [
                        tag_labels[tag_key] for tag_key, _count in related_tags
                    ],
                }
            )

        return {
            "generated_at": reference_time.isoformat().replace("+00:00", "Z"),
            "window_hours": bounded_hours,
            "total_posts": analyzed_post_count,
            "total_tags": len(tag_aggregates),
            "tags": result_tags,
        }

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
        comment_count: int | None,
        like_count: int | None,
        view_count: int | None = None,
        source_rank: int | None = None,
        captured_at: datetime | None = None,
        crawl_status: str = "success",
        crawl_error: str | None = None,
    ) -> dict | None:
        captured_at = captured_at or self._now()
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        native_comment_count = self._optional_native_count(comment_count)
        native_like_count = self._optional_native_count(like_count)
        native_view_count = self._optional_native_count(view_count)

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
                    comment_count=native_comment_count,
                    like_count=native_like_count,
                    view_count=native_view_count,
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
                    comment_count=native_comment_count or 0,
                    like_count=native_like_count or 0,
                    view_count=native_view_count,
                    source_rank=source_rank,
                    crawl_status=crawl_status,
                    crawl_error=crawl_error,
                )
            )
            board.native_comment_count = native_comment_count
            board.native_like_count = native_like_count
            board.native_view_count = native_view_count
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

    def analyze_board(
        self,
        board_id: str,
        analyzer: LLM | None = None,
        *,
        force: bool = False,
        vision_extractor: VisionTextClient | None = None,
        media_root=None,
    ) -> dict | None:
        analyzer = analyzer or LLM()

        with get_session_factory()() as session:
            board = session.get(Board, board_id)
            if board is None:
                return None
            if self._has_complete_analysis(board) and not force:
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

            analysis_text = self._analysis_text(
                board,
                vision_extractor=vision_extractor,
                media_root=media_root,
            )
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
                if board.analysis_status == self.ANALYSIS_FAILED:
                    board.analysis_status = self.ANALYSIS_PENDING
                    board.analysis_retry_count = 0
                    board.analysis_started_at = None
                    board.analysis_error = None
                elif (
                    board.analysis_status == self.ANALYSIS_PENDING
                    and board.analysis_error == VISION_FALLBACK_UNAVAILABLE_ERROR
                ):
                    board.analysis_retry_count = 0
                    board.analysis_error = None
                elif board.analysis_status is None:
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
            if image_path.stat().st_size > analysis_vision_max_image_bytes():
                raise VisionTextError("image file exceeds the configured size limit")
            validate_image_file(
                image_path,
                max_pixels=analysis_vision_max_pixels(),
            )
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
        *,
        vision_extractor: VisionTextClient | None = None,
        media_root=None,
    ) -> dict | None:
        analyzer = analyzer or LLM()
        board_id = self._claim_next_analysis_job(max_retry_count=max_retry_count)
        if board_id is None:
            return None

        try:
            result = self.analyze_board(
                board_id,
                analyzer=analyzer,
                vision_extractor=vision_extractor,
                media_root=media_root,
            )
            if result is None:
                return None
            return {**result, "status": self.ANALYSIS_DONE}
        except RetryableAnalysisError as exc:
            return self._record_analysis_failure(
                board_id,
                error=str(exc),
                max_retry_count=max_retry_count,
                retryable=True,
            )
        except LLMError as exc:
            return self._record_analysis_failure(
                board_id,
                error=str(exc),
                max_retry_count=max_retry_count,
                retryable=exc.retryable,
            )

    def _claim_next_analysis_job(self, max_retry_count: int) -> str | None:
        now = self._now()
        stale_cutoff = now - self.PROCESSING_STALE_AFTER
        heatmap_window_start = now - RECENT_CRAWL_WINDOW

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
                    or_(
                        Board.analysis_status == self.ANALYSIS_PENDING,
                        (
                            (Board.analysis_status == self.ANALYSIS_FAILED)
                            & (Board.analysis_retry_count < max_retry_count)
                            & or_(
                                Board.analysis_error.is_(None),
                                Board.analysis_error.notin_(TERMINAL_ANALYSIS_ERRORS),
                            )
                        ),
                    ),
                    Board.analysis_retry_count < max_retry_count,
                    or_(
                        Board.analysis_requested_at.is_(None),
                        Board.analysis_requested_at <= now,
                    ),
                )
                .order_by(
                    desc(Board.analysis_priority),
                    case((Board.created_at >= heatmap_window_start, 0), else_=1),
                    func.coalesce(
                        Board.analysis_requested_at,
                        Board.created_at,
                    ),
                    Board.created_at,
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

    def _record_analysis_failure(
        self,
        board_id: str,
        error: str,
        max_retry_count: int,
        *,
        retryable: bool = False,
    ) -> dict | None:
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
            if retryable:
                board.analysis_status = self.ANALYSIS_PENDING
                board.analysis_retry_count = min(
                    retry_count,
                    max(max_retry_count - 1, 0),
                )
                board.analysis_requested_at = now + timedelta(
                    seconds=analysis_retryable_backoff_seconds()
                )
                board.analysis_priority = max(
                    int(board.analysis_priority or 0) - 1,
                    0,
                )
            elif retry_count >= max_retry_count:
                board.analysis_status = self.ANALYSIS_FAILED
            else:
                board.analysis_status = self.ANALYSIS_PENDING
                board.analysis_priority = max(int(board.analysis_priority or 0) - 1, 0)
                board.analysis_requested_at = now + timedelta(
                    seconds=analysis_retryable_backoff_seconds()
                )

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
                    and board.native_comment_count is not None
                    else board.native_comment_count
                ),
                like_count=(
                    current_snapshot.like_count
                    if current_snapshot is not None and board.native_like_count is not None
                    else board.native_like_count
                ),
                view_count=(
                    current_snapshot.view_count
                    if current_snapshot is not None and board.native_view_count is not None
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
    def _optional_native_count(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return None

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
        filters = filters or BoardListFilters()
        ordering = desc(self._effective_score_expression(daily=daily))
        stmt = self._apply_list_filters(select(Board), filters)
        secondary_ordering = desc(Board.like_count) if daily else desc(Board.created_at)
        score_as_of = self._now()

        with get_session_factory()() as session:
            if filters.is_default:
                boards = self._list_balanced_candidates(
                    session,
                    stmt=stmt,
                    ordering=ordering,
                    secondary_ordering=secondary_ordering,
                    daily=daily,
                    score_as_of=score_as_of,
                    target_count=offset + page_size,
                )
                boards = boards[offset : offset + page_size]
                return [self._to_dict(board, score_as_of=score_as_of) for board in boards]

            boards = session.scalars(
                stmt.order_by(ordering, secondary_ordering, desc(Board.created_at))
                .offset(offset)
                .limit(page_size)
            ).all()

            return [self._to_dict(board, score_as_of=score_as_of) for board in boards]

    def _list_balanced_candidates(
        self,
        session,
        *,
        stmt,
        ordering,
        secondary_ordering,
        daily: bool,
        score_as_of: datetime,
        target_count: int,
    ) -> list[Board]:
        sites = session.scalars(
            select(Board.site).distinct().order_by(Board.site)
        ).all()
        candidates: list[RankingCandidate[Board]] = []
        score_attr = "daily_score" if daily else "hot_score"
        decay_hours = DAILY_DECAY_HOURS if daily else HOT_DECAY_HOURS

        for site in sites:
            site_boards = session.scalars(
                stmt.where(Board.site == site)
                .order_by(ordering, secondary_ordering, desc(Board.created_at))
                .limit(target_count)
            ).all()
            for board in site_boards:
                updated_at = board.score_updated_at or board.created_at
                candidates.append(
                    RankingCandidate(
                        item=board,
                        identity=str(board.id),
                        site=str(board.site or ""),
                        score=self._effective_score_value(
                            getattr(board, score_attr),
                            updated_at,
                            score_as_of,
                            decay_hours,
                        ),
                        created_at=board.created_at,
                        is_active=self._is_active_ranking_candidate(
                            board,
                            score_as_of=score_as_of,
                            daily=daily,
                        ),
                    )
                )

        return balance_site_exposure(candidates, limit=target_count)

    @staticmethod
    def _is_active_ranking_candidate(
        board: Board,
        *,
        score_as_of: datetime,
        daily: bool,
    ) -> bool:
        activity_at = board.metrics_crawled_at or board.score_updated_at or board.created_at
        if activity_at.tzinfo is None:
            activity_at = activity_at.replace(tzinfo=timezone.utc)
        if score_as_of.tzinfo is None:
            score_as_of = score_as_of.replace(tzinfo=timezone.utc)
        active_hours = DAILY_ACTIVE_SITE_HOURS if daily else HOT_ACTIVE_SITE_HOURS
        return activity_at >= score_as_of - timedelta(hours=active_hours)

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

        if tag := _clean_tag_value(filters.tag):
            # Decode JSON elements before comparing: serialized Korean tags may
            # contain Unicode escapes, and LIKE also treats % and _ as wildcards.
            if get_engine().dialect.name == "postgresql":
                tag_array = case(
                    (func.json_typeof(Board.tags) == "array", Board.tags),
                    else_=cast("[]", JSON),
                )
                tag_values = func.json_array_elements_text(tag_array).table_valued("value")
            else:
                tag_array = case(
                    (func.json_type(Board.tags) == "array", Board.tags),
                    else_="[]",
                )
                tag_values = func.json_each(tag_array).table_valued("value")

            whitespace = " \t\n\r\f\v"
            normalized_tag = func.lower(
                func.trim(
                    func.ltrim(func.trim(tag_values.c.value, whitespace), "#"),
                    whitespace,
                )
            )
            stmt = stmt.where(
                select(1)
                .select_from(tag_values)
                .where(normalized_tag == tag.lower())
                .correlate(Board)
                .exists()
            )

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
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _analysis_text(
        cls,
        board: Board,
        *,
        vision_extractor: VisionTextClient | None = None,
        media_root=None,
    ) -> str:
        contents = normalize_contents(board.contents)
        minimum_body_chars = analysis_min_body_chars()
        minimum_language_chars = analysis_min_language_chars()
        if not has_sufficient_analysis_body(
            contents,
            title=board.title,
            min_body_chars=minimum_body_chars,
            min_language_chars=minimum_language_chars,
        ):
            contents = cls._enrich_analysis_contents_with_vision(
                board.id,
                contents,
                vision_extractor=vision_extractor,
                media_root=media_root,
                title=board.title,
                minimum_body_chars=minimum_body_chars,
                minimum_language_chars=minimum_language_chars,
            )

        if not has_sufficient_analysis_body(
            contents,
            title=board.title,
            min_body_chars=minimum_body_chars,
            min_language_chars=minimum_language_chars,
        ):
            raise LLMError(INSUFFICIENT_ANALYSIS_CONTENT_ERROR)

        return extract_llm_text(
            board.title,
            contents,
            max_chars=analysis_max_input_chars(),
        )

    @staticmethod
    def _enrich_analysis_contents_with_vision(
        board_id: str,
        contents: list[dict[str, str]],
        *,
        vision_extractor: VisionTextClient | None,
        media_root,
        title: object,
        minimum_body_chars: int,
        minimum_language_chars: int,
    ) -> list[dict[str, str]]:
        max_images = analysis_vision_max_images()
        if not analysis_vision_fallback_enabled() or max_images <= 0:
            return contents

        enriched = [dict(block) for block in contents]
        extractor = vision_extractor
        attempted_images = 0
        retryable_vision_failures = 0
        permanent_vision_failures = 0
        max_image_bytes = analysis_vision_max_image_bytes()
        max_image_pixels = analysis_vision_max_pixels()

        for block in enriched:
            if has_sufficient_analysis_body(
                enriched,
                title=title,
                min_body_chars=minimum_body_chars,
                min_language_chars=minimum_language_chars,
            ):
                break
            if block.get("type") != "image" or attempted_images >= max_images:
                continue

            media_path = block.get("media_path")
            if not media_path:
                continue

            try:
                image_path = resolve_media_path(media_path, media_root=media_root)
                if image_path.stat().st_size > max_image_bytes:
                    logger.warning(
                        "Skipping oversized analysis image for board %s",
                        board_id,
                    )
                    continue
                validate_image_file(
                    image_path,
                    max_pixels=max_image_pixels,
                )
            except (OSError, VisionTextError) as exc:
                logger.warning(
                    "Skipping unusable analysis image for board %s: %s",
                    board_id,
                    exc,
                )
                continue

            try:
                if extractor is None:
                    extractor = VisionTextClient()
                attempted_images += 1
                vision_text = extractor.extract_text(
                    image_path,
                    prompt=analysis_vision_prompt(),
                ).strip()
            except (OSError, VisionTextError) as exc:
                if isinstance(exc, VisionTextError) and not exc.retryable:
                    permanent_vision_failures += 1
                else:
                    retryable_vision_failures += 1
                logger.warning(
                    "Vision fallback failed for board %s: %s",
                    board_id,
                    exc,
                )
                continue
            except Exception as exc:
                retryable_vision_failures += 1
                logger.exception(
                    "Unexpected vision fallback failure for board %s: %s",
                    board_id,
                    exc,
                )
                continue

            if not vision_text:
                continue
            existing_text = block.get("text", "").strip()
            if existing_text and vision_text not in existing_text:
                block["text"] = f"{existing_text}\n{vision_text}"
            else:
                block["text"] = vision_text

        still_insufficient = not has_sufficient_analysis_body(
            enriched,
            title=title,
            min_body_chars=minimum_body_chars,
            min_language_chars=minimum_language_chars,
        )
        if still_insufficient and retryable_vision_failures:
            raise RetryableAnalysisError(VISION_FALLBACK_UNAVAILABLE_ERROR)
        if still_insufficient and permanent_vision_failures:
            raise LLMError(VISION_FALLBACK_REJECTED_ERROR)

        return enriched

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


def _clean_tag_value(value: str | None) -> str | None:
    cleaned = _clean_filter_value(value)
    return cleaned.lstrip("#").strip() or None if cleaned else None


def _split_filter_values(values: list[str]) -> list[str]:
    cleaned_values = []
    for value in values:
        for candidate in str(value).split(","):
            cleaned = candidate.strip()
            if cleaned and cleaned not in cleaned_values:
                cleaned_values.append(cleaned)
    return cleaned_values
