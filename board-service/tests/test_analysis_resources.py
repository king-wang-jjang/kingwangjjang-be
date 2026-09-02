import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres  # noqa: E402
from app.db.models import Board  # noqa: E402
from app.repositories.boards import BoardRepository  # noqa: E402


def _board(board_id: str, status: str, created_at: datetime, **values) -> Board:
    return Board(
        id=board_id,
        category="community",
        no=1,
        site="test",
        title=board_id,
        url=f"https://example.com/{board_id}",
        contents="body with enough detail",
        analysis_status=status,
        created_at=created_at,
        **values,
    )


def test_analysis_queue_metrics_exposes_backlog_age_and_recent_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    repository = BoardRepository()

    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                _board("ready", "pending", now - timedelta(minutes=20)),
                _board(
                    "deferred",
                    "pending",
                    now - timedelta(minutes=10),
                    analysis_requested_at=now + timedelta(minutes=5),
                ),
                _board(
                    "processing",
                    "processing",
                    now - timedelta(minutes=40),
                    analysis_started_at=now - timedelta(minutes=15),
                ),
                _board(
                    "done",
                    "done",
                    now - timedelta(hours=2),
                    analysis_updated_at=now - timedelta(minutes=30),
                    gpt_answer="summary",
                    tags=["done"],
                ),
                _board(
                    "failed",
                    "failed",
                    now - timedelta(hours=3),
                    analysis_updated_at=now - timedelta(hours=2),
                ),
            ]
        )
        session.commit()

    metrics = repository.get_analysis_queue_metrics(as_of=now)

    assert metrics == {
        "generated_at": now,
        "total_count": 5,
        "pending_count": 2,
        "ready_pending_count": 1,
        "deferred_pending_count": 1,
        "processing_count": 1,
        "done_count": 1,
        "failed_count": 1,
        "stale_processing_count": 1,
        "oldest_pending_at": now - timedelta(minutes=20),
        "oldest_pending_age_seconds": 1200,
        "recent_arrivals": 3,
        "recent_completions": 1,
    }
