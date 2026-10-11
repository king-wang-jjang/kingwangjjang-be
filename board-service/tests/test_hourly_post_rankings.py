import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import postgres
from app.db.models import Board, HourlyTop10Snapshot
from app.repositories.boards import BoardRepository
from app.routes.boards import router


NOW = datetime(2026, 10, 11, 15, 35, tzinfo=timezone.utc)


@pytest.fixture
def repository(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    monkeypatch.setattr(BoardRepository, "_now", staticmethod(lambda: NOW))
    repo = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(Board(
            id="live", category="issue", no=1, site="dcinside", title="현재 인기글",
            url="https://example.com/live", created_at=NOW, daily_score=100,
            score_updated_at=NOW,
        ))
        session.commit()
    yield repo
    postgres.get_session_factory.cache_clear()
    postgres.get_engine.cache_clear()


def test_only_observed_history_is_returned_and_current_hour_matches_live_top10(repository):
    current_hour = NOW.replace(minute=0)
    observed_hour = current_hour - timedelta(hours=2)
    historical_post = {
        "board_id": "deleted", "rank": 1, "title": "당시 제목", "site": "ppomppu",
        "url": "https://example.com/old",
    }
    with postgres.get_session_factory()() as session:
        session.add_all([
            HourlyTop10Snapshot(started_at=observed_hour, captured_at=observed_hour + timedelta(minutes=55), posts=[historical_post]),
            # A stored current-hour result must not override the actual live ranking.
            HourlyTop10Snapshot(started_at=current_hour, captured_at=current_hour, posts=[historical_post]),
            HourlyTop10Snapshot(started_at=current_hour + timedelta(hours=1), captured_at=NOW + timedelta(hours=1), posts=[historical_post]),
        ])
        session.commit()

    timeline = repository.get_hourly_post_rankings(6)
    buckets = timeline["rankings"]
    assert len(buckets) == 6
    assert buckets[0]["started_at"] == current_hour - timedelta(hours=5)
    assert buckets[3]["posts"] == [historical_post]
    assert buckets[3]["captured_at"] == observed_hour + timedelta(minutes=55)
    assert buckets[4] == {"started_at": current_hour - timedelta(hours=1), "captured_at": None, "is_live": False, "posts": []}
    assert all(bucket["posts"] == [] for bucket in buckets[:3])
    assert buckets[-1]["is_live"] is True
    assert buckets[-1]["captured_at"] == NOW
    assert [post["board_id"] for post in buckets[-1]["posts"]] == [board["id"] for board in repository.list_daily(0, 10)]
    assert buckets[-1]["posts"][0]["rank"] == 1
    # UTC 15:00 crosses Korean midnight without resetting the 6-hour timeline.
    assert buckets[-1]["started_at"].isoformat() == "2026-10-11T15:00:00+00:00"


def test_empty_capture_is_distinct_from_missing_history(repository):
    previous_hour = NOW.replace(minute=0) - timedelta(hours=1)
    with postgres.get_session_factory()() as session:
        session.add(HourlyTop10Snapshot(started_at=previous_hour, captured_at=previous_hour + timedelta(minutes=5), posts=[]))
        session.commit()
    buckets = repository.get_hourly_post_rankings()["rankings"]
    assert len(buckets) == 24
    assert buckets[-2]["posts"] == []
    assert buckets[-2]["captured_at"] is not None
    assert buckets[-3]["captured_at"] is None


def test_hourly_rankings_endpoint_labels_sources_and_validates_window(repository):
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/api/boards/daily/hourly-rankings?hours=12")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    timeline = response.json()
    assert timeline["window_hours"] == 12
    assert len(timeline["rankings"]) == 12
    assert timeline["rankings"][-1]["posts"][0]["site_label"] == "디시인사이드"
    assert timeline["rankings"][-1]["is_live"] is True
    assert timeline["rankings"][0]["captured_at"] is None
    for hours in (0, 5, 25):
        assert client.get(f"/api/boards/daily/hourly-rankings?hours={hours}").status_code == 422
