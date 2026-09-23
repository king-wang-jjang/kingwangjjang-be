import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.principal import Principal
from app.db import postgres
from app.db.models import Board, RecommendationProfile
from app.repositories.recommendations import RecommendationRepository
from app.routes.recommendations import router
from app.services.recommendations import (
    InterestEvent, InterestMutation, InterestProfile, apply_mutation, clean_profile,
    interest_scores, rank_recommendations,
)

NOW = datetime.now(timezone.utc)
HEADERS = {"X-Auth-Status": "authenticated", "X-User-Id": "alice", "X-Auth-Provider": "kakao"}


def event(kind="open", board_id="game", tags=None, at=NOW, identifier="event-1"):
    return InterestEvent(id=identifier, kind=kind, boardId=board_id, tags=tags or ["게임"], at=at)


@pytest.fixture
def repository(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recommendations.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    repo = RecommendationRepository()
    with postgres.get_session_factory()() as session:
        session.add_all([
            Board(id="game", category="free", site="dcinside", title="게임 소식", url="https://example.com/game", tags=["#게임"], created_at=NOW - timedelta(hours=1), hot_score=1),
            Board(id="sport", category="free", site="theqoo", title="스포츠 소식", url="https://example.com/sport", tags=["스포츠"], created_at=NOW - timedelta(hours=1), hot_score=2),
            Board(id="old", category="free", site="dcinside", title="오래된 글", url="https://example.com/old", tags=["게임"], created_at=NOW - timedelta(days=8), hot_score=999),
        ])
        session.commit()
    yield repo
    postgres.get_engine().dispose()
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()


@pytest.fixture
def client(repository):
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_interest_uses_strongest_daily_signal_and_splits_tags():
    profile = InterestProfile(events=[
        event("open", tags=["#AI", "게임"]),
        event("source", tags=["ai", "게임"], identifier="source"),
        event("source", tags=["ＡＩ", "게임"], identifier="reopened"),
    ])
    assert interest_scores(profile, NOW) == {"ai": 1.5, "게임": 1.5}


def test_decay_expiry_and_explicit_preferences():
    profile = InterestProfile(events=[event(at=NOW - timedelta(days=14)), event(board_id="old", tags=["과거"], at=NOW - timedelta(days=31), identifier="old")], followedTags=["AI"], hiddenTags=["과거"])
    assert interest_scores(profile, NOW) == {"게임": 1, "ai": 10}
    assert len(clean_profile(profile, NOW).events) == 1


def test_reset_rejects_late_events_and_disabled_profiles_do_not_collect():
    profile = apply_mutation(InterestProfile(), InterestMutation(id="reset", kind="reset", at=NOW), NOW)
    profile = apply_mutation(profile, InterestMutation(id="late", kind="record", at=NOW - timedelta(seconds=1), events=[event()]), NOW)
    assert profile.events == []
    disabled = apply_mutation(InterestProfile(enabled=False), InterestMutation(id="open", kind="record", at=NOW, events=[event()]), NOW)
    assert disabled.events == []
    assert interest_scores(disabled, NOW) == {}


def test_rankings_explore_hide_dismiss_and_have_stable_order():
    candidates = [{"id": f"game-{index}", "tags": ["게임"], "site": "a" if index % 2 else "b", "created_at": NOW, "hot_score": 1} for index in range(10)]
    candidates += [{"id": "discover", "tags": ["여행"], "site": "c", "created_at": NOW, "hot_score": 1}, {"id": "hidden", "tags": ["정치"], "site": "c", "created_at": NOW, "hot_score": 100}]
    profile = InterestProfile(followedTags=["게임"], hiddenTags=["정치"], events=[event("dismiss", board_id="game-0")])
    ranked = rank_recommendations(candidates, profile, NOW)
    assert ranked[4]["id"] == "discover"
    assert {"hidden", "game-0"}.isdisjoint(row["id"] for row in ranked)
    assert ranked == rank_recommendations(list(reversed(candidates)), profile, NOW)
    assert "관심 태그" in ranked[0]["reason"]


def test_anonymous_recommendation_never_persists_profile(client):
    response = client.post("/api/boards/recommendations", json={"profile": InterestProfile(followedTags=["게임"]).model_dump(mode="json")})
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "game"
    assert "old" not in [row["id"] for row in response.json()["items"]]
    assert response.headers["cache-control"] == "private, no-store"
    with postgres.get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(RecommendationProfile)) == 0
    assert client.get("/api/boards/recommendations/profile").status_code == 401
    assert client.post("/api/boards/recommendations/profile", json={"mutations": []}).status_code == 401


def test_server_resolves_tags_and_deduplicates_retries(client):
    mutation = InterestMutation(id="record-1", kind="record", at=NOW, events=[event(tags=["偽造"])]).model_dump(mode="json")
    for _ in range(2):
        response = client.post("/api/boards/recommendations/profile", headers=HEADERS, json={"mutations": [mutation]})
        assert response.status_code == 200
    assert len(response.json()["events"]) == 1
    assert response.json()["events"][0]["tags"] == ["게임"]
    # Supplying somebody else's interests in a signed-in recommendation request is ignored.
    result = client.post("/api/boards/recommendations", headers=HEADERS, json={"profile": InterestProfile(hiddenTags=["게임"]).model_dump(mode="json")})
    assert "game" in [row["id"] for row in result.json()["items"]]


def test_accounts_and_auth_providers_are_isolated(client):
    mutation = InterestMutation(id="follow", at=NOW, kind="follow", tag="게임").model_dump(mode="json")
    client.post("/api/boards/recommendations/profile", headers=HEADERS, json={"mutations": [mutation]})
    for headers in [{**HEADERS, "X-User-Id": "bob"}, {**HEADERS, "X-Auth-Provider": "local"}]:
        assert client.get("/api/boards/recommendations/profile", headers=headers).json()["followedTags"] == []


def test_import_once_preserves_existing_hidden_preferences(client):
    hidden = InterestMutation(id="hide", at=NOW, kind="hide", tag="게임")
    imported = InterestMutation(id="merge:guest", at=NOW, kind="merge", profile=InterestProfile(followedTags=["게임", "스포츠"], events=[event()]))
    payload = {"mutations": [hidden.model_dump(mode="json"), imported.model_dump(mode="json")]}
    client.post("/api/boards/recommendations/profile", headers=HEADERS, json=payload)
    removed = InterestMutation(id="unfollow", at=NOW, kind="unfollow", tag="스포츠")
    client.post("/api/boards/recommendations/profile", headers=HEADERS, json={"mutations": [removed.model_dump(mode="json")]})
    response = client.post("/api/boards/recommendations/profile", headers=HEADERS, json=payload)
    assert response.json()["followedTags"] == []
    assert response.json()["hiddenTags"] == ["게임"]
    assert len(response.json()["events"]) == 1


def test_filters_and_frozen_id_pages(client):
    result = client.post("/api/boards/recommendations", json={"tag": "게임", "sites": ["dcinside"]}).json()
    assert [row["id"] for row in result["items"]] == ["game"]
    response = client.post("/api/boards/recommendations/posts", json={"ids": ["sport", "game", "deleted"]})
    assert [post["_id"] for post in response.json()] == ["sport", "game"]
    assert client.post("/api/boards/recommendations/posts", json={"ids": ["game"] * 31}).status_code == 422
    assert client.post("/api/boards/recommendations", json={"profile": {"events": [event().model_dump(mode="json")] * 501}}).status_code == 422


def test_concurrent_updates_keep_both_devices_preferences(repository):
    principal = Principal("alice", "kakao", True)
    repository.update_profile(principal, [])
    mutations = [InterestMutation(id=f"follow-{index}", at=NOW, kind="follow", tag=f"태그{index}") for index in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda mutation: repository.update_profile(principal, [mutation]), mutations))
    assert set(repository.get_profile(principal).followedTags) == {f"태그{index}" for index in range(4)}


def test_expired_history_is_physically_removed_for_inactive_accounts(repository):
    principal = Principal("alice", "kakao", True)
    repository.update_profile(principal, [InterestMutation(id="record", at=NOW, kind="record", events=[event()]), InterestMutation(id="follow", at=NOW, kind="follow", tag="게임")])
    assert repository.cleanup_expired(NOW + timedelta(days=31)) == 1
    with postgres.get_session_factory()() as session:
        row = session.scalar(select(RecommendationProfile))
        assert row.data["events"] == []
        assert row.data["followedTags"] == ["게임"]
        assert row.cleanup_at is None


def test_actions_after_reset_click_are_not_discarded_during_network_delay():
    reset_time = NOW - timedelta(seconds=5)
    reset = InterestMutation(id="reset", kind="reset", at=reset_time)
    profile = apply_mutation(InterestProfile(), reset, NOW)
    follow = InterestMutation(id="follow", kind="follow", at=reset_time + timedelta(seconds=1), tag="게임")
    assert apply_mutation(profile, follow, NOW).followedTags == ["게임"]
