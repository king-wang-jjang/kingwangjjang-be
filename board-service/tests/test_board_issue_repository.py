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
        created_at=created_at,
        hot_score=hot_score,
        score_updated_at=created_at,
    )


def test_issue_overview_aggregates_category_impact_momentum_and_context(
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
    assert overview["total_categories"] == 2
    assert [item["category"] for item in overview["categories"]] == [
        "humor",
        "stock",
    ]

    humor = overview["categories"][0]
    assert humor["post_count"] == 3
    assert humor["current_posts"] == 2
    assert humor["previous_posts"] == 1
    assert humor["momentum_percent"] == 50.0
    assert humor["impact_score"] == pytest.approx(15.6091)
    assert humor["share"] == pytest.approx(0.846059)
    assert humor["top_sites"] == [
        {"site": "dcinside", "post_count": 2},
        {"site": "ppomppu", "post_count": 1},
    ]
    assert humor["top_tags"] == ["이슈", "생활", "유머"]


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
                ),
                _board(
                    "pp",
                    category="deal",
                    site="ppomppu",
                    created_at=as_of,
                    hot_score=4,
                ),
            ]
        )
        session.commit()

    overview = repository.get_issue_overview(
        sites=("ppomppu",),
        as_of=as_of,
    )

    assert overview["total_posts"] == 1
    assert [item["category"] for item in overview["categories"]] == ["deal"]
