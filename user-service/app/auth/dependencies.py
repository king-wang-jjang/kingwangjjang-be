import os

import jwt
from fastapi import HTTPException, Request, status
from jwt.exceptions import InvalidTokenError

from app.auth.principal import Principal


def get_optional_principal(request: Request) -> Principal:
    auth_status = request.headers.get("X-Auth-Status", "unauthenticated")
    user_id = request.headers.get("X-User-Id")
    auth_provider = request.headers.get("X-Auth-Provider")
    role = "admin" if request.headers.get("X-User-Role") == "admin" else "user"
    is_authenticated = auth_status == "authenticated" and bool(user_id)
    return Principal(
        user_id=user_id,
        auth_provider=auth_provider,
        is_authenticated=is_authenticated,
        role=role,
    )


def require_principal(request: Request) -> Principal:
    principal = get_optional_principal(request)
    if not principal.is_authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return principal


def configured_admin_user_ids() -> set[str]:
    return {
        user_id.strip()
        for user_id in os.getenv("ADMIN_USER_IDS", "").split(",")
        if user_id.strip()
    }


def require_admin(request: Request) -> Principal:
    principal = require_principal(request)
    token = request.cookies.get("access_token")
    secret_key = os.getenv("JWT_SECRET_KEY")
    payload = {}
    if token and secret_key:
        try:
            payload = jwt.decode(
                token, secret_key, algorithms=["HS256"],
                options={"require": ["exp", "user_id", "auth_provider"]},
            )
        except (InvalidTokenError, TypeError, ValueError):
            pass

    if (
        principal.role != "admin"
        or str(payload.get("user_id", "")) != principal.user_id
        or payload.get("auth_provider") != principal.auth_provider
        or payload.get("type") == "refresh"
        or principal.user_id not in configured_admin_user_ids()
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator required")
    return principal
