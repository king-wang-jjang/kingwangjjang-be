import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board, BoardMetricSnapshot
from app.repositories.boards import BoardListFilters, BoardRepository


@pytest.mark.parametrize("list_method", ["list_realtime", "list_daily"])
@pytest.mark.parametrize(
    ("stored_tag", "filter_tag"),
    [
        ("유머", "유머"),
        ("  ## 유머 \t", "유머"),
        ("유머", " #유머 "),
        ("AI", "ai"),
        ('게임 "패치"', '게임 "패치"'),
        ("개발\\도구", "개발\\도구"),
        ("100%_할인", "100%_할인"),
    ],
)
def test_tag_filters_match_decoded_labels_before_pagination(
    monkeypatch, tmp_path, list_method, stored_tag, filter_tag
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'tag-filter.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    repository = BoardRepository()
    created_at = datetime.now(timezone.utc)
    tags_by_id = {
        "match-first": [stored_tag, stored_tag],
        "match-second": [stored_tag],
        "partial-match": [f"{stored_tag} 관련"],
        "wildcard-lookalike": [stored_tag.replace("%", "퍼센트").replace("_", "특가") + "!"],
        "null-tags": None,
        "empty-tags": [],
        "legacy-object": {"tag": stored_tag},
        "legacy-string": stored_tag,
    }
    with postgres.get_session_factory()() as session:
        for index, (board_id, tags) in enumerate(tags_by_id.items()):
            session.add(
                Board(
                    id=board_id,
                    category="humor",
                    no=index,
                    site="dcinside",
                    title=board_id,
                    url=f"https://example.com/{board_id}",
                    contents=[],
                    tags=tags,
                    created_at=created_at - timedelta(minutes=index),
                )
            )
        session.commit()

    list_boards = getattr(repository, list_method)
    filters = BoardListFilters.from_values(tag=filter_tag)

    assert [row["id"] for row in list_boards(0, 1, filters=filters)] == ["match-first"]
    assert [row["id"] for row in list_boards(1, 1, filters=filters)] == ["match-second"]
    assert list_boards(2, 1, filters=filters) == []


def test_every_home_issue_tag_can_find_its_source_posts(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'home-tags.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    repository = BoardRepository()
    created_at = datetime.now(timezone.utc)

    with postgres.get_session_factory()() as session:
        session.add(
            Board(
                id="home-issue",
                category="humor",
                no=1,
                site="dcinside",
                title="home issue",
                url="https://example.com/home-issue",
                contents=[],
                tags=["#유머", " AI ", "100%_할인"],
                analysis_status=BoardRepository.ANALYSIS_DONE,
                created_at=created_at,
            )
        )
        session.commit()

    overview = repository.get_issue_overview(as_of=created_at)
    assert {tag["tag"] for tag in overview["tags"]} == {"유머", "AI", "100%_할인"}
    for tag in overview["tags"]:
        for source in tag["top_sites"]:
            rows = repository.list_realtime(
                0,
                30,
                filters=BoardListFilters.from_values(tag=tag["tag"], sites=[source["site"]]),
            )
            assert [row["id"] for row in rows] == ["home-issue"]


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


def test_explicit_multi_site_filter_keeps_plain_score_order(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    created_at = datetime.now(timezone.utc)
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                Board(
                    id="dc-first",
                    category="humor",
                    no=1,
                    site="dcinside",
                    title="dc first",
                    url="https://example.com/dc/1",
                    contents=[],
                    created_at=created_at,
                    hot_score=100,
                    score_updated_at=created_at,
                ),
                Board(
                    id="dc-second",
                    category="humor",
                    no=2,
                    site="dcinside",
                    title="dc second",
                    url="https://example.com/dc/2",
                    contents=[],
                    created_at=created_at - timedelta(minutes=1),
                    hot_score=90,
                    score_updated_at=created_at,
                ),
                Board(
                    id="ppomppu-first",
                    category="humor",
                    no=3,
                    site="ppomppu",
                    title="ppomppu first",
                    url="https://example.com/ppomppu/1",
                    contents=[],
                    created_at=created_at - timedelta(minutes=2),
                    hot_score=10,
                    score_updated_at=created_at,
                ),
            ]
        )
        session.commit()

    rows = repository.list_realtime(
        0,
        3,
        filters=BoardListFilters(sites=("dcinside", "ppomppu")),
    )

    assert [row["id"] for row in rows] == [
        "dc-first",
        "dc-second",
        "ppomppu-first",
    ]
