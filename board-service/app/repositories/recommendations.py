import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only

from app.auth.principal import Principal
from app.db.models import Board, RecommendationProfile
from app.db.postgres import get_session_factory
from app.repositories.boards import BoardListFilters, BoardRepository
from app.services.recommendations import (
    InterestMutation, InterestProfile, apply_mutation, clean_profile, clean_tags,
    interest_scores, rank_recommendations,
)


def owner_key(principal: Principal) -> str:
    if not principal.is_authenticated or not principal.user_id:
        raise ValueError("authenticated principal required")
    return hashlib.sha256(json.dumps([principal.auth_provider, principal.user_id]).encode()).hexdigest()


def next_cleanup(profile: InterestProfile):
    return min((event.at for event in profile.events), default=None) + timedelta(days=30, seconds=1) if profile.events else None


class RecommendationRepository:
    def __init__(self):
        self.boards = BoardRepository()

    def get_profile(self, principal: Principal) -> InterestProfile:
        with get_session_factory()() as session:
            row = session.get(RecommendationProfile, owner_key(principal))
            profile = InterestProfile.model_validate(row.data) if row else InterestProfile()
        return clean_profile(profile, datetime.now(timezone.utc))

    def update_profile(self, principal: Principal, mutations: list[InterestMutation]) -> InterestProfile:
        owner = owner_key(principal)
        now = datetime.now(timezone.utc)
        # Resolve board tags from authoritative data, including imported anonymous events.
        ids = {event.boardId for mutation in mutations
               for event in (mutation.events + (mutation.profile.events if mutation.profile else []))
               if event.kind != "tag" and event.boardId}
        with get_session_factory()() as session:
            boards = session.execute(select(Board.id, Board.tags).where(Board.id.in_(ids))).all() if ids else []
        tags_by_id = {row.id: clean_tags(row.tags if isinstance(row.tags, list) else [], 20) for row in boards}
        for mutation in mutations:
            for events in [mutation.events, mutation.profile.events if mutation.profile else []]:
                for event in events:
                    if event.kind != "tag":
                        event.tags = tags_by_id.get(event.boardId, [])
        # Compare-and-swap prevents two browsers from overwriting each other's events.
        for _attempt in range(8):
            with get_session_factory()() as session:
                row = session.get(RecommendationProfile, owner)
                revision = row.revision if row else None
                data = row.data if row else {}
                profile = InterestProfile.model_validate(data)
                receipts = data.get("_receipts", [])
                imports = data.get("_imports", [])
                for mutation in mutations:
                    if mutation.id in receipts or (mutation.kind == "merge" and mutation.id in imports):
                        continue
                    profile = apply_mutation(profile, mutation, now)
                    receipts = (receipts + [mutation.id])[-1000:]
                    if mutation.kind == "merge":
                        imports = (imports + [mutation.id])[-100:]
                saved = {**profile.model_dump(mode="json"), "_receipts": receipts, "_imports": imports}
                if revision is None:
                    session.add(RecommendationProfile(owner=owner, data=saved, revision=1, updated_at=now, cleanup_at=next_cleanup(profile)))
                    try:
                        session.commit()
                        return profile
                    except IntegrityError:
                        session.rollback()
                        continue
                result = session.execute(update(RecommendationProfile).where(
                    RecommendationProfile.owner == owner, RecommendationProfile.revision == revision,
                ).values(data=saved, revision=revision + 1, updated_at=now, cleanup_at=next_cleanup(profile)))
                session.commit()
                if result.rowcount == 1:
                    return profile
        raise RuntimeError("recommendation_profile_conflict")

    def cleanup_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        with get_session_factory()() as session:
            rows = session.scalars(select(RecommendationProfile).where(
                RecommendationProfile.cleanup_at <= now,
            ).order_by(RecommendationProfile.cleanup_at).limit(100)).all()
            for row in rows:
                profile = clean_profile(InterestProfile.model_validate(row.data), now)
                session.execute(update(RecommendationProfile).where(
                    RecommendationProfile.owner == row.owner, RecommendationProfile.revision == row.revision,
                ).values(data={**row.data, **profile.model_dump(mode="json")}, revision=row.revision + 1,
                         cleanup_at=next_cleanup(profile)))
            session.commit()
        return len(rows)

    def recommend(self, profile: InterestProfile, filters: BoardListFilters) -> list[dict]:
        now = datetime.now(timezone.utc)
        scores = interest_scores(profile, now)
        tags = sorted((tag for tag in scores if scores[tag] > 0), key=lambda tag: -scores[tag])[:10]
        base = BoardRepository._apply_list_filters(select(Board), filters).where(
            Board.created_at >= now - timedelta(days=7), Board.created_at <= now,
        ).options(load_only(Board.id, Board.site, Board.tags, Board.hot_score, Board.created_at))
        candidates: dict[str, dict] = {}
        statements = [base.order_by(desc(Board.created_at), Board.id).limit(300),
                      base.order_by(desc(Board.hot_score).nullslast(), desc(Board.created_at), Board.id).limit(300)]
        if not filters.tag:
            statements += [BoardRepository._apply_list_filters(base, BoardListFilters(tag=tag))
                           .order_by(desc(Board.created_at), Board.id).limit(50) for tag in tags]
        with get_session_factory()() as session:
            for statement in statements:
                for board in session.scalars(statement):
                    candidates[board.id] = {
                        "id": board.id, "site": board.site,
                        "tags": board.tags if isinstance(board.tags, list) else [],
                        "created_at": board.created_at, "hot_score": board.hot_score,
                    }
        return rank_recommendations(list(candidates.values()), profile, now)

    def get_posts(self, ids: list[str]) -> list[dict]:
        with get_session_factory()() as session:
            boards = session.scalars(select(Board).where(Board.id.in_(ids))).all()
            by_id = {board.id: self.boards._to_dict(board) for board in boards}
        return [by_id[board_id] for board_id in dict.fromkeys(ids) if board_id in by_id]
