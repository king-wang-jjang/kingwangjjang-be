import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board
from app.repositories.boards import BoardListFilters, BoardRepository


def test_list_realtime_applies_board_filters_before_pagination(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                Board(
                    id="board-match",
                    category="humor",
                    no=1,
                    site="dcinside",
                    title="seed title with filter target",
                    url="https://example.com/post/1",
                    contents=[],
                    tags=["funny", "issue"],
                    thumbnail="Dcinside/humor/1/image.webp",
                    created_at=created_at + timedelta(minutes=3),
                ),
                Board(
                    id="board-wrong-site",
                    category="humor",
                    no=2,
                    site="ygosu",
                    title="seed title with filter target",
                    url="https://example.com/post/2",
                    contents=[],
                    tags=["funny"],
                    thumbnail="Ygosu/humor/2/image.webp",
                    created_at=created_at + timedelta(minutes=2),
                ),
                Board(
                    id="board-missing-thumbnail",
                    category="humor",
                    no=3,
                    site="dcinside",
                    title="seed title with filter target",
                    url="https://example.com/post/3",
                    contents=[],
                    tags=["funny"],
                    thumbnail=None,
                    created_at=created_at + timedelta(minutes=1),
                ),
            ]
        )
        session.commit()

    rows = repository.list_realtime(
        0,
        1,
        filters=BoardListFilters(
            sites=("dcinside",),
            category="humor",
            tag="funny",
            query="filter target",
            has_thumbnail=True,
        ),
    )

    assert [row["id"] for row in rows] == ["board-match"]
