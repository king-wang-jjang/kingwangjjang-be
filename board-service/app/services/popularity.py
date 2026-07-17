from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, isfinite, log1p, sqrt
from typing import Any


SITE_WEIGHTS = {
    "dcinside": 1.0,
    "ygosu": 1.0,
    "ppomppu": 1.0,
    "theqoo": 1.0,
}

ALGORITHM_VERSION = 2
DEFAULT_INTERVAL_MINUTES = 20.0
MIN_INTERVAL_SCALE = 0.25
MAX_INTERVAL_SCALE = 4.0
HOT_DECAY_HOURS = 12.0
DAILY_DECAY_HOURS = 36.0


@dataclass(frozen=True)
class PopularityMetrics:
    site: str
    created_at: datetime
    captured_at: datetime
    comment_count: int = 0
    like_count: int = 0
    view_count: int | None = None
    source_rank: int | None = None
    previous_comment_count: int | None = None
    previous_like_count: int | None = None
    previous_view_count: int | None = None
    previous_delta_comments: int = 0
    previous_delta_likes: int = 0
    previous_delta_views: int = 0
    llm_engagement_score: float | None = None
    previous_captured_at: datetime | None = None
    previous_interval_minutes: float | None = None


@dataclass(frozen=True)
class PopularityScores:
    hot_score: float
    daily_score: float
    breakdown: dict[str, Any]


def calculate_popularity_scores(metrics: PopularityMetrics) -> PopularityScores:
    comment_count = _clean_count(metrics.comment_count)
    like_count = _clean_count(metrics.like_count)
    view_count = _clean_count(metrics.view_count)
    raw_delta_comments = _delta(comment_count, metrics.previous_comment_count)
    raw_delta_likes = _delta(like_count, metrics.previous_like_count)
    raw_delta_views = _delta(view_count, metrics.previous_view_count)

    current_interval_minutes = _interval_minutes(
        metrics.captured_at,
        metrics.previous_captured_at,
    )
    current_interval_scale = _interval_scale(current_interval_minutes)
    previous_interval_minutes = _clean_interval(metrics.previous_interval_minutes)
    previous_interval_scale = _interval_scale(previous_interval_minutes)

    delta_comments = raw_delta_comments * current_interval_scale
    delta_likes = raw_delta_likes * current_interval_scale
    delta_views = raw_delta_views * current_interval_scale
    previous_delta_comments = (
        _clean_count(metrics.previous_delta_comments) * previous_interval_scale
    )
    previous_delta_likes = _clean_count(metrics.previous_delta_likes) * previous_interval_scale
    previous_delta_views = _clean_count(metrics.previous_delta_views) * previous_interval_scale

    total_component = (
        1.2 * log1p(comment_count)
        + 1.8 * log1p(like_count)
        + 0.2 * log1p(view_count)
    )
    velocity_component = _weighted_velocity(
        delta_comments,
        delta_likes,
        delta_views,
    )
    previous_velocity_component = _weighted_velocity(
        previous_delta_comments,
        previous_delta_likes,
        previous_delta_views,
    )
    acceleration_component = min(
        max(velocity_component - previous_velocity_component, 0.0),
        2.0,
    )
    source_rank_component = _source_rank_component(metrics.source_rank)
    hot_source_rank_addend = 2.0 * source_rank_component
    daily_source_rank_addend = 1.5 * source_rank_component
    llm_engagement_score = _clean_llm_engagement_score(metrics.llm_engagement_score)
    llm_engagement_signal = (llm_engagement_score - 50.0) / 50.0
    hot_llm_addend = 1.5 * llm_engagement_signal
    daily_llm_addend = 1.0 * llm_engagement_signal
    age_hours = _age_hours(metrics.created_at, metrics.captured_at)
    site_weight = SITE_WEIGHTS.get(metrics.site, 1.0)

    raw_hot_score = max(
        0.35 * total_component
        + 0.55 * velocity_component
        + acceleration_component
        + hot_source_rank_addend
        + hot_llm_addend,
        0.0,
    )
    raw_daily_score = max(
        0.65 * total_component
        + 0.25 * velocity_component
        + daily_source_rank_addend
        + daily_llm_addend,
        0.0,
    )

    hot_age_decay = exp(-age_hours / HOT_DECAY_HOURS)
    daily_age_decay = exp(-age_hours / DAILY_DECAY_HOURS)
    hot_score = raw_hot_score * site_weight * hot_age_decay
    daily_score = raw_daily_score * site_weight * daily_age_decay

    return PopularityScores(
        hot_score=hot_score,
        daily_score=daily_score,
        breakdown={
            "algorithm_version": ALGORITHM_VERSION,
            "comment_count": comment_count,
            "like_count": like_count,
            "view_count": view_count,
            "raw_delta_comments": raw_delta_comments,
            "raw_delta_likes": raw_delta_likes,
            "raw_delta_views": raw_delta_views,
            "current_interval_minutes": current_interval_minutes,
            "current_interval_scale": current_interval_scale,
            "previous_interval_minutes": previous_interval_minutes,
            "previous_interval_scale": previous_interval_scale,
            "delta_comments_20m": delta_comments,
            "delta_likes_20m": delta_likes,
            "delta_views_20m": delta_views,
            "previous_delta_comments_20m": previous_delta_comments,
            "previous_delta_likes_20m": previous_delta_likes,
            "previous_delta_views_20m": previous_delta_views,
            "total_component": total_component,
            "velocity_component": velocity_component,
            "previous_velocity_component": previous_velocity_component,
            "acceleration_component": acceleration_component,
            "source_rank": metrics.source_rank,
            "source_rank_component": source_rank_component,
            "hot_source_rank_addend": hot_source_rank_addend,
            "daily_source_rank_addend": daily_source_rank_addend,
            "llm_engagement_score": llm_engagement_score,
            "llm_engagement_signal": llm_engagement_signal,
            "hot_llm_addend": hot_llm_addend,
            "daily_llm_addend": daily_llm_addend,
            "raw_hot_score": raw_hot_score,
            "raw_daily_score": raw_daily_score,
            "age_hours": age_hours,
            "hot_age_decay": hot_age_decay,
            "daily_age_decay": daily_age_decay,
            "site_weight": site_weight,
        },
    )


def _clean_count(value: int | None) -> int:
    if value is None:
        return 0
    return max(int(value), 0)


def _delta(current: int, previous: int | None) -> int:
    if previous is None:
        return 0
    return max(current - int(previous), 0)


def _weighted_velocity(comments: float, likes: float, views: float) -> float:
    return (
        2.4 * log1p(comments)
        + 3.2 * log1p(likes)
        + 0.3 * log1p(views)
    )


def _interval_minutes(captured_at: datetime, previous_captured_at: datetime | None) -> float | None:
    if previous_captured_at is None:
        return None
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    if previous_captured_at.tzinfo is None:
        previous_captured_at = previous_captured_at.replace(tzinfo=timezone.utc)
    return _clean_interval((captured_at - previous_captured_at).total_seconds() / 60)


def _clean_interval(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        interval = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(interval) or interval <= 0:
        return None
    return interval


def _interval_scale(interval_minutes: float | None) -> float:
    if interval_minutes is None:
        return 1.0
    scale = DEFAULT_INTERVAL_MINUTES / interval_minutes
    return min(max(scale, MIN_INTERVAL_SCALE), MAX_INTERVAL_SCALE)


def _clean_llm_engagement_score(value: float | None) -> float:
    if value is None:
        return 50.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 50.0
    if not isfinite(score):
        return 50.0
    return min(max(score, 0.0), 100.0)


def _source_rank_component(source_rank: int | None) -> float:
    if source_rank is None or source_rank <= 0:
        return 0
    return 1 / sqrt(source_rank)


def _age_hours(created_at: datetime, captured_at: datetime) -> float:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    return max((captured_at - created_at).total_seconds() / 3600, 0)
