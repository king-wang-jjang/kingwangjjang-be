import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board, BoardMetricSnapshot
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


def test_list_recently_crawled_sites_uses_successful_snapshots_from_last_24_hours(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'recent-sites.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    now = datetime(2026, 7, 27, 12, tzinfo=timezone.utc)
    boards = [
        Board(
            id=f"board-{site}",
            category="popular",
            no=index,
            site=site,
            title=f"{site} title",
            url=f"https://example.com/{site}",
            contents=[],
            created_at=now - timedelta(days=10),
        )
        for index, site in enumerate(
            ("dcinside", "fmkorea", "ygosu", "arca", "new-community", "future-site"),
            start=1,
        )
    ]
    with postgres.get_session_factory()() as session:
        session.add_all(boards)
        session.flush()
        session.add_all(
            [
                BoardMetricSnapshot(
                    board_id="board-dcinside",
                    captured_at=now - timedelta(minutes=5),
                    crawl_status="success",
                ),
                BoardMetricSnapshot(
                    board_id="board-dcinside",
                    captured_at=now - timedelta(minutes=1),
                    crawl_status="success",
                ),
                BoardMetricSnapshot(
                    board_id="board-fmkorea",
                    captured_at=now - timedelta(hours=24),
                    crawl_status="success",
                ),
                BoardMetricSnapshot(
                    board_id="board-ygosu",
                    captured_at=now - timedelta(hours=24, seconds=1),
                    crawl_status="success",
                ),
                BoardMetricSnapshot(
                    board_id="board-arca",
                    captured_at=now - timedelta(minutes=1),
                    crawl_status="failed",
                    crawl_error="blocked",
                ),
                BoardMetricSnapshot(
                    board_id="board-new-community",
                    captured_at=now - timedelta(hours=2),
                    crawl_status="success",
                ),
                BoardMetricSnapshot(
                    board_id="board-future-site",
                    captured_at=now + timedelta(minutes=1),
                    crawl_status="success",
                ),
            ]
        )
        session.commit()

    assert repository.list_recently_crawled_sites(as_of=now) == [
        "dcinside",
        "fmkorea",
        "new-community",
    ]
    assert repository.list_recently_crawled_sites(
        as_of=now.astimezone(timezone(timedelta(hours=9)))
    ) == [
        "dcinside",
        "fmkorea",
        "new-community",
    ]
    assert repository.list_recently_crawled_sites(
        as_of=now + timedelta(hours=25)
    ) == []
