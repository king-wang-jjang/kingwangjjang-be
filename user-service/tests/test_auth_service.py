import asyncio
import builtins
import datetime
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")

from app.models.auth_models import UserType
from app.routes.auth import _cookie_secure
from app.services.auth_service import JWTService, KakaoAuthService, UserService


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

    def test_refresh_token_uses_browser_maximum_400_day_lifetime(self):
        token = JWTService.create_refresh_token("123", "kakao")
        payload = jwt.decode(token, os.environ["JWT_REFRESH_SECRET_KEY"], algorithms=["HS256"])

        self.assertEqual(payload["type"], "refresh")
        self.assertEqual(payload["exp"] - payload["iat"], 400 * 24 * 60 * 60)
        self.assertEqual(JWTService.decode_refresh_token(token)["user_id"], "123")

    def test_rotate_session_rejects_a_token_that_is_not_current(self):
        token = JWTService.create_refresh_token("123", "kakao")

        class FakeRepository:
            def get_user(self, user_id, auth_provider):
                return {"refresh_token": "another-token"}

        with patch("app.services.auth_service.UserRepository", return_value=FakeRepository()):
            self.assertIsNone(UserService.rotate_session(token))

    def test_rotate_session_replaces_the_stored_refresh_token(self):
        token = JWTService.create_refresh_token("123", "kakao")

        class FakeRepository:
            def __init__(self):
                self.rotated = None

            def get_user(self, user_id, auth_provider):
                return {"refresh_token": token}

            def rotate_refresh_token(
                self,
                user_id,
                auth_provider,
                current_refresh_token,
                next_refresh_token,
            ):
                self.rotated = (
                    user_id,
                    auth_provider,
                    current_refresh_token,
                    next_refresh_token,
                )
                return True

        repository = FakeRepository()
        with patch("app.services.auth_service.UserRepository", return_value=repository):
            access_token, next_refresh_token = UserService.rotate_session(token)

        self.assertNotEqual(next_refresh_token, token)
        self.assertEqual(
            repository.rotated,
            ("123", "kakao", token, next_refresh_token),
        )
        self.assertEqual(JWTService.decode_access_token(access_token)["user_id"], "123")

    def test_rotate_session_rejects_a_token_that_loses_the_atomic_rotation(self):
        token = JWTService.create_refresh_token("123", "kakao")

        class FakeRepository:
            def get_user(self, user_id, auth_provider):
                return {"refresh_token": token}

            def rotate_refresh_token(
                self,
                user_id,
                auth_provider,
                current_refresh_token,
                next_refresh_token,
            ):
                return False

        with patch("app.services.auth_service.UserRepository", return_value=FakeRepository()):
            self.assertIsNone(UserService.rotate_session(token))

    def test_save_user_to_db_uses_user_repository(self):
        class FakeRepository:
            def __init__(self):
                self.saved = None

            def get_or_create_user(self, user_id, auth_provider, nickname=None, profile_image=None, refresh_token=None):
                self.saved = (user_id, auth_provider, nickname, profile_image, refresh_token)
                return {"user_id": user_id, "refresh_token": refresh_token}

        repository = FakeRepository()
        user_info = UserType(
            user_id="123",
            auth_provider="kakao",
            nickname="왕짱",
            profile_image="https://k.kakaocdn.net/profile.jpg",
        )
        with patch("app.services.auth_service.UserRepository", lambda: repository):
            saved = UserService.save_user_to_db(user_info, "refresh-token")

        self.assertEqual(saved, {"user_id": "123", "refresh_token": "refresh-token"})
        self.assertEqual(
            repository.saved,
            ("123", "kakao", "왕짱", "https://k.kakaocdn.net/profile.jpg", "refresh-token"),
        )

    def test_fetch_user_info_maps_kakao_profile_fields(self):
        kakao_payload = {
            "id": 123,
            "kakao_account": {
                "profile": {
                    "nickname": "왕짱",
                    "profile_image_url": "https://k.kakaocdn.net/profile.jpg",
                    "thumbnail_image_url": "https://k.kakaocdn.net/thumb.jpg",
                }
            },
        }

        async def run():
            with patch("app.services.auth_service._get_json", return_value=kakao_payload):
                return await KakaoAuthService.fetch_user_info("access-token", "kakao")

        user_info = asyncio.run(run())

        self.assertIsNotNone(user_info)
        self.assertEqual(user_info.user_id, "123")
        self.assertEqual(user_info.auth_provider, "kakao")
        self.assertEqual(user_info.nickname, "왕짱")
        self.assertEqual(user_info.profile_image, "https://k.kakaocdn.net/profile.jpg")


if __name__ == "__main__":
    unittest.main()
