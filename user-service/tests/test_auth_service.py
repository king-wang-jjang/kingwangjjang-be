import datetime
import os
import sys
import unittest
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")

from app.models.auth_models import UserType
from app.routes.auth import _cookie_secure
from app.services.auth_service import JWTService, UserService


class FakeUsers:
    def __init__(self):
        self.user = None
        self.updated = None
        self.inserted = None

    def find_user(self, query):
        if self.user and self.user.get("user_id") == query.get("user_id"):
            return self.user
        return None

    def insert_user(self, document):
        self.inserted = document
        self.user = document
        return True

    def update_user(self, query, update_values):
        self.updated = (query, update_values)
        self.user.update(update_values)
        return True


class AuthServiceTests(unittest.TestCase):
    def test_cookie_secure_defaults_to_true(self):
        os.environ.pop("AUTH_COOKIE_SECURE", None)

        self.assertTrue(_cookie_secure())

    def test_cookie_secure_can_be_disabled_for_local_dev(self):
        os.environ["AUTH_COOKIE_SECURE"] = "FALSE"

        self.assertFalse(_cookie_secure())

    def test_access_token_round_trips_user_identity(self):
        token = JWTService.create_access_token("123", "kakao")

        decoded = JWTService.decode_access_token(token)

        self.assertEqual(decoded["user_id"], "123")
        self.assertEqual(decoded["auth_provider"], "kakao")

    def test_save_user_to_db_inserts_new_user_with_refresh_token(self):
        users = FakeUsers()
        user_info = UserType(user_id="123", auth_provider="kakao")

        saved = UserService.save_user_to_db(user_info, "refresh-token", users)

        self.assertEqual(saved["user_id"], "123")
        self.assertEqual(saved["auth_provider"], "kakao")
        self.assertEqual(saved["refresh_token"], "refresh-token")
        self.assertIsInstance(saved["create_time"], datetime.datetime)

    def test_save_user_to_db_updates_existing_refresh_token_without_insert(self):
        users = FakeUsers()
        users.user = {"user_id": "123", "auth_provider": "kakao", "refresh_token": "old"}
        user_info = UserType(user_id="123", auth_provider="kakao")

        saved = UserService.save_user_to_db(user_info, "new-refresh-token", users)

        self.assertEqual(saved["user_id"], "123")
        self.assertIsNone(users.inserted)
        self.assertEqual(
            users.updated,
            (
                {"user_id": "123"},
                {"refresh_token": "new-refresh-token", "auth_provider": "kakao"},
            ),
        )


if __name__ == "__main__":
    unittest.main()
