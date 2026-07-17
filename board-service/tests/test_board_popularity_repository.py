import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board, BoardMetricSnapshot
from app.repositories.boards import BoardRepository


def test_record_metric_snapshot_updates_scores_and_latest_native_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    created_at = datetime(2026, 6, 23, 9, tzinfo=timezone.utc)
    first_capture = datetime(2026, 6, 23, 9, 10, tzinfo=timezone.utc)
    second_capture = datetime(2026, 6, 23, 9, 30, tzinfo=timezone.utc)

    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="board-1",
                category="humor",
                no=1,
                site="dcinside",
                title="seed title",
                url="https://example.com/1",
                contents=[],
                created_at=created_at,
            )
        )
        session.commit()

    repository.record_metric_snapshot(
        "board-1",
        comment_count=2,
        like_count=1,
        captured_at=first_capture,
        source_rank=5,
    )
    result = repository.record_metric_snapshot(
        "board-1",
        comment_count=10,
        like_count=6,
        captured_at=second_capture,
        source_rank=2,
    )

    assert result is not None
    assert result["native_comment_count"] == 10
    assert result["native_like_count"] == 6
    assert result["source_rank"] == 2
    assert result["hot_score"] > 0
    assert result["daily_score"] > 0
    assert result["score_breakdown"]["delta_comments_20m"] == 8
    assert result["score_breakdown"]["delta_likes_20m"] == 5

    with postgres.get_session_factory()() as session:
        snapshots = session.query(BoardMetricSnapshot).order_by(BoardMetricSnapshot.captured_at).all()
        board = session.get(Board, "board-1")

    assert len(snapshots) == 2
    assert snapshots[1].comment_count == 10
    assert board.native_comment_count == 10
    assert board.native_like_count == 6
    assert board.metrics_crawled_at.replace(tzinfo=timezone.utc) == second_capture


def test_realtime_and_daily_lists_order_by_popularity_scores(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    created_at = datetime(2026, 6, 23, 9, tzinfo=timezone.utc)
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                Board(
                    id="cold-new",
                    category="humor",
                    no=1,
                    site="dcinside",
                    title="new but cold",
                    url="https://example.com/1",
                    contents=[],
                    created_at=created_at + timedelta(minutes=20),
                    hot_score=1,
                    daily_score=1,
                ),
                Board(
                    id="hot-older",
                    category="humor",
                    no=2,
                    site="dcinside",
                    title="older but hot",
                    url="https://example.com/2",
                    contents=[],
                    created_at=created_at,
                    hot_score=10,
                    daily_score=20,
                ),
            ]
        )
        session.commit()

    assert [row["id"] for row in repository.list_realtime(0, 10)] == ["hot-older", "cold-new"]
    assert [row["id"] for row in repository.list_daily(0, 10)] == ["hot-older", "cold-new"]


def test_lists_apply_decay_after_the_last_score_update(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    now = datetime.now(timezone.utc)
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                Board(
                    id="stale-high-score",
                    category="humor",
                    no=10,
                    site="dcinside",
                    title="stale",
                    url="https://example.com/stale",
                    contents=[],
                    created_at=now - timedelta(days=10),
                    hot_score=10,
                    daily_score=10,
                    score_updated_at=now - timedelta(hours=120),
                ),
                Board(
                    id="fresh-lower-score",
                    category="humor",
                    no=11,
                    site="dcinside",
                    title="fresh",
                    url="https://example.com/fresh",
                    contents=[],
                    created_at=now,
                    hot_score=1,
                    daily_score=1,
                    score_updated_at=now,
                ),
            ]
        )
        session.commit()

    realtime = repository.list_realtime(0, 2)
    daily = repository.list_daily(0, 2)

    assert realtime[0]["id"] == "fresh-lower-score"
    assert realtime[0]["hot_score"] > realtime[1]["hot_score"]
    assert daily[0]["id"] == "fresh-lower-score"
    assert daily[0]["daily_score"] > daily[1]["daily_score"]
