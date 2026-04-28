import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.seed import SEED_BOARD_IDS, seed_boards


def test_seed_boards_dry_run_returns_development_boards():
    rows = seed_boards(dry_run=True)

    assert [row["id"] for row in rows] == SEED_BOARD_IDS
    assert rows[0]["title"] == "seed title 1"
    assert rows[0]["comment_count"] == 2
    assert rows[1]["site"] == "ygosu"
