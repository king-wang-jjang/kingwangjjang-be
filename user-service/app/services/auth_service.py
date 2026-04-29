import asyncio
import datetime
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.config import Config
from app.models.auth_models import UserType
from app.repositories.users import UserRepository


KAKAO_API_BASE = "https://kapi.kakao.com"


def _post_form(url: str, data: dict) -> dict:
    payload = urlencode(data).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, headers: dict) -> dict:
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


class KakaoAuthService:
    @staticmethod
    async def fetch_access_token(code: str, client_id: str, redirect_uri: str, client_secret: str) -> str | None:
        token_data = await asyncio.to_thread(
            _post_form,
            "https://kauth.kakao.com/oauth/token",
            {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        return token_data.get("access_token")

    @staticmethod
    async def fetch_user_info(access_token: str, auth_provider: str = "kakao") -> UserType | None:
        if not access_token:
            return None

        user_data = await asyncio.to_thread(
            _get_json,
            f"{KAKAO_API_BASE}/v2/user/me",
            {"Authorization": f"Bearer {access_token}"},
        )
        return UserType(user_id=str(user_data["id"]), auth_provider=auth_provider)


class UserService:
    @staticmethod
    def save_user_to_db(
        user_info: UserType,
        refresh_token: str,
        db_controller=None,
    ) -> dict:
        if db_controller is None:
            return UserService._save_user_to_postgres(user_info, refresh_token)

        controller = db_controller
        user_id = str(user_info.user_id)
        auth_provider = user_info.auth_provider
        existing_user = controller.find_user({"user_id": user_id})

        if existing_user:
            update_data = {
                "refresh_token": refresh_token,
                "auth_provider": auth_provider,
            }
            controller.update_user({"user_id": user_id}, update_data)
            return {**existing_user, **update_data}

        user_document = {
            "user_id": user_id,
            "auth_provider": auth_provider,
            "refresh_token": refresh_token,
            "nickname": getattr(user_info, "nickname", None),
            "profile_image": getattr(user_info, "profile_image", None),
            "create_time": datetime.datetime.now(datetime.UTC),
        }
        controller.insert_user(user_document)
        return user_document

    @staticmethod
    def _save_user_to_postgres(user_info: UserType, refresh_token: str) -> dict:
        return UserRepository().get_or_create_user(
            user_id=str(user_info.user_id),
            auth_provider=user_info.auth_provider,
            nickname=getattr(user_info, "nickname", None),
            profile_image=getattr(user_info, "profile_image", None),
            refresh_token=refresh_token,
        )


class JWTService:
    @staticmethod
    def _config_value(name: str) -> str:
        value = Config().get_env(name)
        if not value:
            raise RuntimeError(f"{name} is required")
        return value

    @classmethod
    def create_access_token(cls, user_id: str, auth_provider: str) -> str:
        now = datetime.datetime.now(datetime.UTC)
        payload = {
            "user_id": str(user_id),
            "auth_provider": auth_provider,
            "iat": now,
            "exp": now + datetime.timedelta(hours=1),
            "iss": "user-service",
        }
        return jwt.encode(payload, cls._config_value("JWT_SECRET_KEY"), algorithm="HS256")

    @classmethod
    def create_refresh_token(cls, user_id: str, auth_provider: str) -> str:
        now = datetime.datetime.now(datetime.UTC)
        payload = {
            "user_id": str(user_id),
            "auth_provider": auth_provider,
            "iat": now,
            "exp": now + datetime.timedelta(days=30),
            "iss": "user-service",
        }
        return jwt.encode(payload, cls._config_value("JWT_REFRESH_SECRET_KEY"), algorithm="HS256")

    @classmethod
    def decode_access_token(cls, access_token: str) -> dict | None:
        try:
            decoded_payload = jwt.decode(access_token, cls._config_value("JWT_SECRET_KEY"), algorithms=["HS256"])
            return {
                "user_id": str(decoded_payload.get("user_id")),
                "auth_provider": decoded_payload.get("auth_provider"),
            }
        except (ExpiredSignatureError, InvalidTokenError):
            return None
