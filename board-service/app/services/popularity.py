from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, log1p, sqrt
from typing import Any


SITE_WEIGHTS = {
    "dcinside": 1.0,
    "ygosu": 1.0,
    "ppomppu": 1.0,
    "theqoo": 1.0,
}


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


@dataclass(frozen=True)
class PopularityScores:
    hot_score: float
    daily_score: float
    breakdown: dict[str, Any]


def calculate_popularity_scores(metrics: PopularityMetrics) -> PopularityScores:
    comment_count = _clean_count(metrics.comment_count)
    like_count = _clean_count(metrics.like_count)
    view_count = _clean_count(metrics.view_count)
    delta_comments = _delta(comment_count, metrics.previous_comment_count)
    delta_likes = _delta(like_count, metrics.previous_like_count)
    delta_views = _delta(view_count, metrics.previous_view_count)

    total_component = (
        1.2 * log1p(comment_count)
        + 1.8 * log1p(like_count)
        + 0.2 * log1p(view_count)
    )
    velocity_component = (
        2.4 * log1p(delta_comments)
        + 3.2 * log1p(delta_likes)
        + 0.3 * log1p(delta_views)
    )
    previous_velocity = (
        _clean_count(metrics.previous_delta_comments)
        + _clean_count(metrics.previous_delta_likes)
        + _clean_count(metrics.previous_delta_views)
    )
    current_velocity = delta_comments + delta_likes + delta_views
    acceleration_component = log1p(max(current_velocity - previous_velocity, 0))
    source_rank_component = _source_rank_component(metrics.source_rank)
    age_hours = _age_hours(metrics.created_at, metrics.captured_at)
    site_weight = SITE_WEIGHTS.get(metrics.site, 1.0)

    raw_hot_score = (
        0.35 * total_component
        + 0.55 * velocity_component
        + 0.10 * source_rank_component
        + acceleration_component
    )
    raw_daily_score = (
        0.65 * total_component
        + 0.25 * velocity_component
        + 0.10 * source_rank_component
    )

    hot_age_decay = exp(-age_hours / 12)
    daily_age_decay = exp(-age_hours / 36)
    hot_score = raw_hot_score * site_weight * hot_age_decay
    daily_score = raw_daily_score * site_weight * daily_age_decay

    return PopularityScores(
        hot_score=hot_score,
        daily_score=daily_score,
        breakdown={
            "comment_count": comment_count,
            "like_count": like_count,
            "view_count": view_count,
            "delta_comments_20m": delta_comments,
            "delta_likes_20m": delta_likes,
            "delta_views_20m": delta_views,
            "total_component": total_component,
            "velocity_component": velocity_component,
            "acceleration_component": acceleration_component,
            "source_rank_component": source_rank_component,
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
