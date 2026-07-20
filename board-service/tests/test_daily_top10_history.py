import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, inspect


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db import postgres
from app.db.models import Board, DailyTop10Snapshot
from app.repositories.boards import BoardRepository


def test_daily_top10_snapshot_model_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    BoardRepository()
    table = DailyTop10Snapshot.__table__
    database = inspect(postgres.get_engine())

    assert table.name == "daily_top10_snapshots"
    assert isinstance(table.c.id.type, String)
    assert table.c.id.type.length == 36
    assert isinstance(table.c.snapshot_date.type, Date)
    assert isinstance(table.c.rank.type, Integer)
    assert isinstance(table.c.daily_score.type, Float)
    assert isinstance(table.c.captured_at.type, DateTime)
    assert table.c.captured_at.type.timezone is True
    assert str(next(iter(table.c.board_id.foreign_keys)).target_fullname) == "boards.id"
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns >= {
        ("snapshot_date", "rank"),
        ("snapshot_date", "board_id"),
    }
    assert {index["name"] for index in database.get_indexes(table.name)} >= {
        "ix_daily_top10_snapshots_snapshot_date"
    }


def test_daily_history_lists_dates_and_ranked_boards_with_snapshot_scores(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'boards.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()

    repository = BoardRepository()
    captured_at = datetime(2026, 7, 20, tzinfo=timezone.utc)
    with postgres.get_session_factory()() as session:
        session.add_all(
            [
                Board(
                    id="board-first",
                    category="humor",
                    no=1,
                    site="dcinside",
                    title="first board",
                    url="https://example.com/first",
                    contents=[],
                    daily_score=1.0,
                    created_at=captured_at,
                ),
                Board(
                    id="board-second",
                    category="humor",
                    no=2,
                    site="dcinside",
                    title="second board",
                    url="https://example.com/second",
                    contents=[],
                    daily_score=999.0,
                    created_at=captured_at,
                ),
            ]
        )
        session.add_all(
            [
                DailyTop10Snapshot(
                    id="snapshot-older",
                    snapshot_date=date(2026, 7, 19),
                    rank=1,
                    board_id="board-first",
                    daily_score=70.0,
                    captured_at=captured_at,
                ),
                DailyTop10Snapshot(
                    id="snapshot-second",
                    snapshot_date=date(2026, 7, 20),
                    rank=2,
                    board_id="board-second",
                    daily_score=80.25,
                    captured_at=captured_at,
                ),
                DailyTop10Snapshot(
                    id="snapshot-first",
                    snapshot_date=date(2026, 7, 20),
                    rank=1,
                    board_id="board-first",
                    daily_score=90.5,
                    captured_at=captured_at,
                ),
            ]
        )
        session.commit()

    assert repository.list_daily_history_dates() == [date(2026, 7, 20), date(2026, 7, 19)]
    assert repository.list_daily_history_dates(limit=1) == [date(2026, 7, 20)]

    history = repository.list_daily_history(date(2026, 7, 20))

    assert [board["id"] for board in history] == ["board-first", "board-second"]
    assert [board["daily_score"] for board in history] == [90.5, 80.25]
    assert repository.list_daily_history(date(2026, 7, 20), limit=1) == [history[0]]
    assert repository.list_daily_history(date(2026, 7, 18)) == []
