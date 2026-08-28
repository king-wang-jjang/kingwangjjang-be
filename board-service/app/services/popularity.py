from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, isfinite, log, log1p, sqrt
from typing import Any, Iterable


@dataclass(frozen=True)
class SitePopularityProfile:
    """Typical engagement for a popular-feed post on one source site.

    These values are scale parameters only. Source-native counters remain
    unchanged in ``boards`` and ``board_metric_snapshots``.
    """

    comment_total: float
    like_total: float
    view_total: float
    comment_velocity: float
    like_velocity: float
    view_velocity: float


DEFAULT_SITE_PROFILE = SitePopularityProfile(
    comment_total=30.0,
    like_total=30.0,
    view_total=5_000.0,
    comment_velocity=5.0,
    like_velocity=5.0,
    view_velocity=1_000.0,
)

# A signal at 1.0 means the post reached the typical level for its site's
# popular feed. Profiles are shared with CrawlScheduler's algorithm v3.
SITE_PROFILES = {
    "dcinside": SitePopularityProfile(60, 100, 12_000, 10, 15, 3_000),
    "ppomppu": SitePopularityProfile(25, 20, 4_000, 4, 3, 800),
    "ygosu": SitePopularityProfile(15, 12, 2_000, 3, 2, 400),
    "theqoo": SitePopularityProfile(120, 50, 30_000, 20, 8, 6_000),
    "fmkorea": SitePopularityProfile(80, 250, 20_000, 15, 40, 4_000),
    "arca": SitePopularityProfile(45, 80, 8_000, 8, 12, 1_600),
    "inven": SitePopularityProfile(20, 25, 3_000, 4, 4, 600),
    "instiz": SitePopularityProfile(40, 30, 8_000, 7, 5, 1_600),
    "ruliweb": SitePopularityProfile(45, 70, 8_000, 8, 10, 1_600),
    "natepan": SitePopularityProfile(80, 150, 20_000, 15, 25, 4_000),
}

ALGORITHM_VERSION = 3
DEFAULT_INTERVAL_MINUTES = 20.0
MIN_INTERVAL_SCALE = 0.25
MAX_INTERVAL_SCALE = 4.0
HOT_DECAY_HOURS = 12.0
DAILY_DECAY_HOURS = 36.0
NORMALIZED_BASELINE_SIGNAL = 1.0 / log(2.0)


@dataclass(frozen=True)
class PopularityMetrics:
    site: str
    created_at: datetime
    captured_at: datetime
    comment_count: int | None = 0
    like_count: int | None = 0
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
    comment_available = metrics.comment_count is not None
    like_available = metrics.like_count is not None
    view_available = metrics.view_count is not None
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

    profile = SITE_PROFILES.get(metrics.site, DEFAULT_SITE_PROFILE)
    normalized_comment_count = _normalized_signal(comment_count, profile.comment_total)
    normalized_like_count = _normalized_signal(like_count, profile.like_total)
    normalized_view_count = _normalized_signal(view_count, profile.view_total)
    total_component, total_available_weight = _weighted_available_component(
        (
            (normalized_comment_count, 1.2, comment_available),
            (normalized_like_count, 1.8, like_available),
            (normalized_view_count, 0.2, view_available),
        )
    )
    normalized_delta_comments = _normalized_signal(
        delta_comments,
        profile.comment_velocity,
    )
    normalized_delta_likes = _normalized_signal(delta_likes, profile.like_velocity)
    normalized_delta_views = _normalized_signal(delta_views, profile.view_velocity)
    velocity_component, velocity_available_weight = _weighted_available_component(
        (
            (normalized_delta_comments, 2.4, comment_available),
            (normalized_delta_likes, 3.2, like_available),
            (normalized_delta_views, 0.3, view_available),
        )
    )
    normalized_previous_delta_comments = _normalized_signal(
        previous_delta_comments,
        profile.comment_velocity,
    )
    normalized_previous_delta_likes = _normalized_signal(
        previous_delta_likes,
        profile.like_velocity,
    )
    normalized_previous_delta_views = _normalized_signal(
        previous_delta_views,
        profile.view_velocity,
    )
    previous_velocity_component, _ = _weighted_available_component(
        (
            (normalized_previous_delta_comments, 2.4, comment_available),
            (normalized_previous_delta_likes, 3.2, like_available),
            (normalized_previous_delta_views, 0.3, view_available),
        )
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
    hot_score = raw_hot_score * hot_age_decay
    daily_score = raw_daily_score * daily_age_decay

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
            "site_profile": metrics.site if metrics.site in SITE_PROFILES else "default",
            "site_baselines": {
                "comment_total": profile.comment_total,
                "like_total": profile.like_total,
                "view_total": profile.view_total,
                "comment_velocity_20m": profile.comment_velocity,
                "like_velocity_20m": profile.like_velocity,
                "view_velocity_20m": profile.view_velocity,
            },
            "metric_availability": {
                "comments": comment_available,
                "likes": like_available,
                "views": view_available,
            },
            "normalized_comment_count": normalized_comment_count,
            "normalized_like_count": normalized_like_count,
            "normalized_view_count": normalized_view_count,
            "normalized_delta_comments_20m": normalized_delta_comments,
            "normalized_delta_likes_20m": normalized_delta_likes,
            "normalized_delta_views_20m": normalized_delta_views,
            "normalized_previous_delta_comments_20m": normalized_previous_delta_comments,
            "normalized_previous_delta_likes_20m": normalized_previous_delta_likes,
            "normalized_previous_delta_views_20m": normalized_previous_delta_views,
            "total_available_weight": total_available_weight,
            "velocity_available_weight": velocity_available_weight,
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


def _normalized_signal(value: float, baseline: float) -> float:
    clean_baseline = baseline if isfinite(baseline) and baseline > 0 else 1.0
    clean_value = max(float(value), 0.0) if isfinite(float(value)) else 0.0
    return log1p(clean_value / clean_baseline) * NORMALIZED_BASELINE_SIGNAL


def _weighted_available_component(
    signals: Iterable[tuple[float, float, bool]],
) -> tuple[float, float]:
    signals = tuple(signals)
    total_weight = sum(weight for _, weight, _ in signals)
    available_weight = sum(weight for _, weight, available in signals if available)
    if available_weight <= 0:
        return 0.0, 0.0
    weighted_sum = sum(
        signal * weight
        for signal, weight, available in signals
        if available
    )
    return weighted_sum * total_weight / available_weight, available_weight


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
