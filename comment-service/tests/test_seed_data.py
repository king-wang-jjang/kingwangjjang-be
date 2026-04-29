import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.seed import seed_comments


def test_seed_comments_dry_run_returns_root_and_reply():
    rows = seed_comments(dry_run=True)

    assert len(rows) == 2
    assert rows[0]["parent_id"] is None
    assert rows[1]["parent_id"] == rows[0]["id"]
    assert rows[0]["reply_count"] == 1
