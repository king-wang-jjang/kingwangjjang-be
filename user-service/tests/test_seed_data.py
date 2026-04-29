import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.seed import seed_users


def test_seed_users_dry_run_returns_dev_user():
    rows = seed_users(dry_run=True)

    assert rows == [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "user_id": "dev-user",
            "auth_provider": "local",
            "nickname": "dev-user",
            "profile_image": None,
            "refresh_token": None,
        }
    ]
