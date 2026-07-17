from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    no: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    site: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    contents: Mapped[list | dict | str | None] = mapped_column(JSON, nullable=True)
    gpt_answer: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    llm_engagement_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_engagement_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    analysis_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_error: Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    native_comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    native_like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    native_view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_metrics_crawl_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hot_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class BoardMetricSnapshot(Base):
    __tablename__ = "board_metric_snapshots"
    __table_args__ = (
        Index("ix_board_metric_snapshots_board_captured_at", "board_id", "captured_at"),
        Index("ix_board_metric_snapshots_captured_at", "captured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    board_id: Mapped[str] = mapped_column(ForeignKey("boards.id"), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crawl_status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    crawl_error: Mapped[str | None] = mapped_column(String, nullable=True)


class BoardLike(Base):
    __tablename__ = "board_likes"
    __table_args__ = (UniqueConstraint("board_id", "user_id", name="uq_board_likes_board_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    board_id: Mapped[str] = mapped_column(ForeignKey("boards.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
