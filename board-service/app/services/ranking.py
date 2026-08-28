from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Generic, Iterable, TypeVar


T = TypeVar("T")

REPEAT_EXPOSURE_PENALTY = 0.5
HOT_ACTIVE_SITE_HOURS = 48.0
DAILY_ACTIVE_SITE_HOURS = 24.0 * 7


@dataclass(frozen=True)
class RankingCandidate(Generic[T]):
    item: T
    identity: str
    site: str
    score: float
    created_at: datetime
    is_active: bool = True


def balance_site_exposure(
    candidates: Iterable[RankingCandidate[T]],
    *,
    limit: int,
) -> list[T]:
    """Return a deterministic, score-aware order with one initial slot per site.

    The first exposure round contains the best candidate from every active site,
    ordered by score. Remaining slots use the original score with a penalty for
    sites that have already appeared. Building a prefix before pagination keeps
    separate page requests stable and prevents duplicates or omissions.
    """
    target = max(int(limit), 0)
    if target == 0:
        return []

    queues: dict[str, list[RankingCandidate[T]]] = defaultdict(list)
    seen_identities: set[str] = set()
    for candidate in candidates:
        if candidate.identity in seen_identities:
            continue
        seen_identities.add(candidate.identity)
        queues[candidate.site].append(candidate)

    for site_candidates in queues.values():
        site_candidates.sort(key=_candidate_sort_key)

    selected: list[T] = []
    exposure_counts: dict[str, int] = defaultdict(int)

    # Coverage is prefix-stable: changing the requested page size never changes
    # which candidates were selected before it.
    first_exposure = []
    for site_candidates in queues.values():
        active_index = next(
            (
                index
                for index, candidate in enumerate(site_candidates)
                if candidate.is_active
            ),
            None,
        )
        if active_index is not None:
            first_exposure.append(site_candidates.pop(active_index))
    first_exposure.sort(key=_candidate_sort_key)
    for candidate in first_exposure:
        if len(selected) >= target:
            return selected
        selected.append(candidate.item)
        exposure_counts[candidate.site] += 1

    while len(selected) < target:
        available = [site_candidates[0] for site_candidates in queues.values() if site_candidates]
        if not available:
            break

        candidate = min(
            available,
            key=lambda value: _selection_sort_key(
                value,
                exposure_count=exposure_counts[value.site],
            ),
        )
        queues[candidate.site].pop(0)
        selected.append(candidate.item)
        exposure_counts[candidate.site] += 1

    return selected


def _selection_sort_key(
    candidate: RankingCandidate[object],
    *,
    exposure_count: int,
) -> tuple[float, float, float, str, str]:
    score = _clean_score(candidate.score)
    exposure_adjusted_score = score / (
        1.0 + REPEAT_EXPOSURE_PENALTY * max(exposure_count, 0)
    )
    return (
        -exposure_adjusted_score,
        -score,
        -_timestamp(candidate.created_at),
        candidate.site,
        candidate.identity,
    )


def _candidate_sort_key(
    candidate: RankingCandidate[object],
) -> tuple[float, float, str, str]:
    return (
        -_clean_score(candidate.score),
        -_timestamp(candidate.created_at),
        candidate.site,
        candidate.identity,
    )


def _clean_score(value: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not isfinite(score):
        return 0.0
    return max(score, 0.0)


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()
