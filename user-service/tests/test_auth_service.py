import builtins
import datetime
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")

from app.models.auth_models import UserType
from app.routes.auth import _cookie_secure
from app.services.auth_service import JWTService, UserService


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

    def test_save_user_to_db_uses_user_repository(self):
        class FakeRepository:
            def __init__(self):
                self.saved = None

            def get_or_create_user(self, user_id, auth_provider, nickname=None, profile_image=None, refresh_token=None):
                self.saved = (user_id, auth_provider, refresh_token)
                return {"user_id": user_id, "refresh_token": refresh_token}

        repository = FakeRepository()
        fake_users_module = types.ModuleType("app.repositories.users")
        fake_users_module.UserRepository = lambda: repository
        
        user_info = UserType(user_id="123", auth_provider="kakao")
        with patch.dict(sys.modules, {"app.repositories.users": fake_users_module}):
            saved = UserService.save_user_to_db(user_info, "refresh-token")

        self.assertEqual(saved, {"user_id": "123", "refresh_token": "refresh-token"})
        self.assertEqual(repository.saved, ("123", "kakao", "refresh-token"))


if __name__ == "__main__":
    unittest.main()
