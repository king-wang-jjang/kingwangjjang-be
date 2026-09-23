"""Bounded, explainable tag interests. No external model or anonymous database profile."""

from datetime import datetime, timedelta, timezone
from math import log1p, sqrt
from typing import Annotated, Literal
from unicodedata import normalize

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

Tag = Annotated[str, StringConstraints(max_length=100)]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=100)]
WEIGHTS = {"tag": 1, "open": 2, "source": 3, "like": 5, "dismiss": -4}
RETENTION = timedelta(days=30)


class InterestEvent(BaseModel):
    id: Identifier
    kind: Literal["tag", "open", "source", "like", "dismiss"]
    at: AwareDatetime
    boardId: Identifier | None = None
    tags: list[Tag] = Field(default_factory=list, max_length=20)


class InterestProfile(BaseModel):
    schemaVersion: Literal[1] = 1
    enabled: bool = True
    events: list[InterestEvent] = Field(default_factory=list, max_length=500)
    followedTags: list[Tag] = Field(default_factory=list, max_length=100)
    hiddenTags: list[Tag] = Field(default_factory=list, max_length=100)
    resetAt: AwareDatetime | None = None


class InterestMutation(BaseModel):
    id: Identifier
    at: AwareDatetime
    kind: Literal["record", "follow", "unfollow", "hide", "unhide", "reset", "enable", "disable", "merge"]
    tag: Tag = ""
    events: list[InterestEvent] = Field(default_factory=list, max_length=500)
    profile: InterestProfile | None = None


def tag_key(value: str) -> str:
    return normalize("NFKC", value).strip().lstrip("#").strip().lower()[:100]


def clean_tags(tags: list[str], limit: int = 100) -> list[str]:
    return list(dict.fromkeys(key for value in tags if isinstance(value, str) and (key := tag_key(value))))[:limit]


def clean_profile(profile: InterestProfile, now: datetime) -> InterestProfile:
    events: dict[str, InterestEvent] = {}
    for event in profile.events:
        if not now - RETENTION <= event.at <= now + timedelta(minutes=5):
            continue
        if profile.resetAt and event.at <= profile.resetAt:
            continue
        tags = clean_tags(event.tags, 20)
        if not tags or (event.kind != "tag" and not event.boardId):
            continue
        # At most one signal of each kind per target/day, even across tabs/devices.
        target = tags[0] if event.kind == "tag" else event.boardId
        key = f"{event.kind}:{target}:{event.at.astimezone(timezone.utc).date()}"
        if key not in events or events[key].at < event.at:
            events[key] = event.model_copy(update={"tags": tags})
    return profile.model_copy(update={
        "events": sorted(events.values(), key=lambda event: event.at)[-500:],
        "followedTags": clean_tags(profile.followedTags),
        "hiddenTags": clean_tags(profile.hiddenTags),
    })


def apply_mutation(profile: InterestProfile, mutation: InterestMutation, now: datetime) -> InterestProfile:
    profile = clean_profile(profile, now)
    if mutation.at > now + timedelta(minutes=5) or mutation.at < now - RETENTION:
        return profile
    if profile.resetAt and mutation.at <= profile.resetAt:
        return profile
    key = tag_key(mutation.tag)
    if mutation.kind == "reset":
        return InterestProfile(enabled=profile.enabled, resetAt=min(mutation.at, now))
    if mutation.kind in {"enable", "disable"}:
        profile.enabled = mutation.kind == "enable"
    elif mutation.kind == "record" and profile.enabled:
        profile.events = (profile.events + mutation.events)[-1000:]
    elif mutation.kind == "merge" and mutation.profile:
        incoming = clean_profile(mutation.profile, now)
        if profile.enabled:
            profile.events = profile.events + incoming.events
        # Import explicit choices without undoing existing hidden tags.
        profile.hiddenTags = clean_tags(profile.hiddenTags + incoming.hiddenTags)
        profile.followedTags = [tag for tag in clean_tags(profile.followedTags + incoming.followedTags)
                                if tag not in profile.hiddenTags]
    elif key:
        if mutation.kind == "follow":
            profile.followedTags = clean_tags(profile.followedTags + [key])
            profile.hiddenTags = [tag for tag in profile.hiddenTags if tag != key]
        elif mutation.kind == "unfollow":
            profile.followedTags = [tag for tag in profile.followedTags if tag != key]
        elif mutation.kind == "hide":
            profile.hiddenTags = clean_tags(profile.hiddenTags + [key])
            profile.followedTags = [tag for tag in profile.followedTags if tag != key]
        elif mutation.kind == "unhide":
            profile.hiddenTags = [tag for tag in profile.hiddenTags if tag != key]
    return clean_profile(profile, now)


def interest_scores(profile: InterestProfile, now: datetime) -> dict[str, float]:
    if not profile.enabled:
        return {}
    profile = clean_profile(profile, now)
    signals: dict[str, InterestEvent] = {}
    for event in profile.events:
        target = event.tags[0] if event.kind == "tag" else event.boardId
        group = "dismiss" if event.kind == "dismiss" else "tag" if event.kind == "tag" else "post"
        key = f"{group}:{target}:{event.at.astimezone(timezone.utc).date()}"
        if key not in signals or WEIGHTS[event.kind] > WEIGHTS[signals[key].kind]:
            signals[key] = event
    scores: dict[str, float] = {}
    for event in signals.values():
        age_days = max(0, (now - event.at).total_seconds() / 86400)
        weight = WEIGHTS[event.kind] * 0.5 ** (age_days / 14) / len(event.tags)
        for tag in event.tags:
            scores[tag] = scores.get(tag, 0) + weight
    for tag in profile.followedTags:
        scores[tag] = max(0, scores.get(tag, 0)) + 10
    return {tag: score for tag, score in scores.items() if tag not in profile.hiddenTags}


def rank_recommendations(candidates: list[dict], profile: InterestProfile, now: datetime, limit: int = 120) -> list[dict]:
    profile = clean_profile(profile, now)
    scores = interest_scores(profile, now)
    maximum = max([1, *[score for score in scores.values() if score > 0]])
    hidden = set(profile.hiddenTags)
    dismissed = {event.boardId for event in profile.events if profile.enabled and event.kind == "dismiss"}
    read = {event.boardId for event in profile.events if profile.enabled and event.kind in {"open", "source"}}
    ranked = []
    for candidate in candidates:
        tags = clean_tags(candidate.get("tags") or [])
        if candidate["id"] in dismissed or hidden.intersection(tags):
            continue
        matching = sorted((tag for tag in tags if scores.get(tag, 0) > 0), key=lambda tag: -scores[tag])
        affinity = max(-1, min(1, sum(scores.get(tag, 0) for tag in tags) / (maximum * sqrt(max(1, len(tags))))))
        created = candidate["created_at"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        freshness = 0.5 ** (max(0, (now - created).total_seconds()) / 86400)
        popularity = min(1, log1p(max(0, candidate.get("hot_score") or 0)) / log1p(100))
        score = (0.6 * affinity + 0.25 * freshness + 0.15 * popularity
                 if scores else 0.6 * freshness + 0.4 * popularity)
        if candidate["id"] in read:
            score -= 0.25
        reason = (f"#{matching[0]} 관심 태그와 관련된 글" if matching[0] in profile.followedTags
                  else f"#{matching[0]} 읽기 활동을 바탕으로 추천") if matching else "새로운 분야의 인기글" if scores else "최근 인기글"
        ranked.append({**candidate, "score": score, "matching": bool(matching), "reason": reason})
    ranked.sort(key=lambda row: (-row["score"], row["id"]))
    result = []
    while ranked and len(result) < limit:
        pool = [row for row in ranked if not row["matching"]] if scores and len(result) % 5 == 4 else []
        pool = pool or ranked
        if len(result) >= 2 and result[-1]["site"] == result[-2]["site"]:
            pool = [row for row in pool if row["site"] != result[-1]["site"]] or pool
        chosen = pool[0]
        result.append(chosen)
        ranked.remove(chosen)
    return [{"id": row["id"], "reason": row["reason"]} for row in result]
