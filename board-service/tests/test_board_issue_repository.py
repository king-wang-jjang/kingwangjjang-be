import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board
from app.repositories.boards import BoardRepository


def _board(
    board_id: str,
    *,
    category: str,
    site: str,
    created_at: datetime,
    hot_score: float,
    tags: list[str] | None = None,
    analysis_status: str = BoardRepository.ANALYSIS_DONE,
) -> Board:
    return Board(
        id=board_id,
        category=category,
        no=1,
        site=site,
        title=board_id,
        url=f"https://example.com/{board_id}",
        contents=[],
        tags=tags,
        analysis_status=analysis_status,
        created_at=created_at,
        hot_score=hot_score,
        score_updated_at=created_at,
    )


def test_issue_overview_aggregates_ai_tag_impact_momentum_and_context(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    as_of = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                _board(
                    "humor-current-1",
                    category="humor",
                    site="dcinside",
                    created_at=as_of,
                    hot_score=9,
                    tags=["이슈", "유머", "이슈"],
                ),
                _board(
                    "humor-current-2",
                    category="humor",
                    site="dcinside",
                    created_at=as_of - timedelta(hours=2),
                    hot_score=4,
                    tags=["이슈"],
                ),
                _board(
                    "humor-previous",
                    category="humor",
                    site="ppomppu",
                    created_at=as_of - timedelta(hours=18),
                    hot_score=1,
                    tags=["생활"],
                ),
                _board(
                    "stock-current",
                    category="stock",
                    site="ygosu",
                    created_at=as_of - timedelta(hours=1),
                    hot_score=2,
                    tags=["증시"],
                ),
                _board(
                    "outside-window",
                    category="old",
                    site="dcinside",
                    created_at=as_of - timedelta(hours=25),
                    hot_score=100,
                ),
                _board(
                    "pending-analysis",
                    category="humor",
                    site="dcinside",
                    created_at=as_of,
                    hot_score=100,
                    tags=["미분석"],
                    analysis_status=BoardRepository.ANALYSIS_PENDING,
                ),
            ]
        )
        session.commit()

    overview = repository.get_issue_overview(
        window_hours=24,
        limit=12,
        as_of=as_of,
    )

    assert overview["generated_at"] == "2026-08-31T12:00:00Z"
    assert overview["total_posts"] == 4
    assert overview["total_tags"] == 4
    assert [item["tag"] for item in overview["tags"]] == [
        "이슈",
        "유머",
        "증시",
        "생활",
    ]

    issue = overview["tags"][0]
    assert issue["post_count"] == 2
    assert issue["current_posts"] == 2
    assert issue["previous_posts"] == 0
    assert issue["momentum_percent"] == 200.0
    assert issue["impact_score"] == pytest.approx(14.3859)
    assert issue["share"] == pytest.approx(0.505672, abs=0.000001)
    assert issue["top_sites"] == [
        {"site": "dcinside", "post_count": 2},
    ]
    assert issue["related_tags"] == ["유머"]


def test_issue_overview_applies_site_scope(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    as_of = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                _board(
                    "dc",
                    category="humor",
                    site="dcinside",
                    created_at=as_of,
                    hot_score=3,
                    tags=["유머"],
                ),
                _board(
                    "pp",
                    category="deal",
                    site="ppomppu",
                    created_at=as_of,
                    hot_score=4,
                    tags=["특가"],
                ),
            ]
        )
        session.commit()

    overview = repository.get_issue_overview(
        sites=("ppomppu",),
        as_of=as_of,
    )

    assert overview["total_posts"] == 1
    assert overview["total_tags"] == 1
    assert [item["tag"] for item in overview["tags"]] == ["특가"]
    assert overview["hourly_rankings"][-1]["tags"] == [
        {"tag": "특가", "post_count": 1, "rank": 1}
    ]


def test_hourly_tag_rankings_align_clock_hours_and_count_unique_analyzed_tags(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'hourly.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    as_of = datetime(2026, 9, 21, 21, 30, tzinfo=timezone(timedelta(hours=9)))
    reference_utc = as_of.astimezone(timezone.utc)
    first_hour = reference_utc.replace(hour=7, minute=0)
    repository = BoardRepository()

    def tagged_board(board_id, created_at, tags, **kwargs):
        return _board(
            board_id,
            category="humor",
            site="dcinside",
            created_at=created_at,
            hot_score=0,
            tags=tags,
            **kwargs,
        )

    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                tagged_board("rolling-start", reference_utc - timedelta(hours=6), ["older"]),
                tagged_board("before-chart", first_hour - timedelta(seconds=1), ["older"]),
                tagged_board("first-boundary", first_hour, [" beta ", "#Alpha", "alpha", "##alpha", ""]),
                tagged_board("first-end", first_hour + timedelta(minutes=59, seconds=59), ["beta"]),
                tagged_board("second-boundary", first_hour + timedelta(hours=1), ["gamma", "delta"]),
                tagged_board("current-hour", reference_utc, ["beta"]),
                tagged_board("future", reference_utc + timedelta(seconds=1), ["future"]),
                tagged_board(
                    "pending",
                    first_hour,
                    ["pending"],
                    analysis_status=BoardRepository.ANALYSIS_PENDING,
                ),
            ]
        )
        session.commit()

    overview = repository.get_issue_overview(window_hours=6, as_of=as_of)
    hourly = overview["hourly_rankings"]

    assert overview["generated_at"] == "2026-09-21T12:30:00Z"
    assert overview["total_posts"] == 6
    assert [point["started_at"] for point in hourly] == [
        f"2026-09-21T{hour:02d}:00:00Z" for hour in range(7, 13)
    ]
    assert hourly[0]["tags"] == [
        {"tag": "beta", "post_count": 2, "rank": 1},
        {"tag": "Alpha", "post_count": 1, "rank": 2},
    ]
    assert hourly[1]["tags"] == [
        {"tag": "delta", "post_count": 1, "rank": 1},
        {"tag": "gamma", "post_count": 1, "rank": 2},
    ]
    assert [point["tags"] for point in hourly[2:5]] == [[], [], []]
    assert hourly[-1]["tags"] == [{"tag": "beta", "post_count": 1, "rank": 1}]


def test_hourly_tag_rankings_choose_top_ten_independently_of_overview_limit(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'top-ten.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    as_of = datetime(2026, 9, 21, 12, 30, tzinfo=timezone.utc)
    repository = BoardRepository()
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                _board(
                    "high-impact-outside-chart",
                    category="humor",
                    site="dcinside",
                    created_at=as_of - timedelta(hours=6),
                    hot_score=100_000,
                    tags=[f"impact-{index}" for index in range(4)],
                ),
                *[
                    _board(
                        f"hourly-{index}",
                        category="humor",
                        site="dcinside",
                        created_at=as_of,
                        hot_score=0,
                        tags=[f"hour-{index:02d}"],
                    )
                    for index in reversed(range(12))
                ],
            ]
        )
        session.commit()

    overview = repository.get_issue_overview(window_hours=6, limit=4, as_of=as_of)

    assert [tag["tag"] for tag in overview["tags"]] == [
        f"impact-{index}" for index in range(4)
    ]
    assert overview["hourly_rankings"][-1]["tags"] == [
        {"tag": f"hour-{index:02d}", "post_count": 1, "rank": index + 1}
        for index in range(10)
    ]


def test_hourly_tag_rankings_keep_empty_hours_when_no_analysis_is_available(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'empty.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    overview = BoardRepository().get_issue_overview(
        window_hours=6,
        as_of=datetime(2026, 9, 21, 12, tzinfo=timezone.utc),
    )

    assert overview["total_posts"] == 0
    assert len(overview["hourly_rankings"]) == 6
    assert overview["hourly_rankings"][0]["started_at"] == "2026-09-21T07:00:00Z"
    assert all(point["tags"] == [] for point in overview["hourly_rankings"])
