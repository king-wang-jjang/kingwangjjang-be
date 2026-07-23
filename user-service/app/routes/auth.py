import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config import Config
from app.services.auth_service import JWTService, KakaoAuthService, UserService


router = APIRouter()
config = Config()
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
ACCESS_TOKEN_MAX_AGE_SECONDS = int(JWTService.ACCESS_TOKEN_TTL.total_seconds())
REFRESH_TOKEN_MAX_AGE_SECONDS = int(JWTService.REFRESH_TOKEN_TTL.total_seconds())


def _cookie_secure() -> bool:
    return os.getenv("AUTH_COOKIE_SECURE", "TRUE").upper() not in {"0", "FALSE", "NO"}


def _is_private_ipv4_hostname(hostname: str) -> bool:
    if hostname.startswith("10.") or hostname.startswith("192.168."):
        return True

    parts = hostname.split(".")
    if len(parts) < 2 or parts[0] != "172":
        return False

    try:
        second_octet = int(parts[1])
    except ValueError:
        return False

    return 16 <= second_octet <= 31


def _is_local_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False
    return hostname in LOCAL_HOSTNAMES or _is_private_ipv4_hostname(hostname)


def _callback_redirect_uri(request: Request) -> str:
    if config.get_env("SERVER_RUN_MODE") == "FALSE" and _is_local_hostname(request.url.hostname):
        return str(request.url.replace(path="/callback", query=""))

    return config.get_env("REDIRECT_URI")


def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_options = {
        "httponly": True,
        "secure": _cookie_secure(),
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE_SECONDS,
        **cookie_options,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE_SECONDS,
        **cookie_options,
    )


@router.get("/login")
def login(request: Request):
    kakao_oauth_url = "https://kauth.kakao.com/oauth/authorize?" + urlencode(
        {
            "client_id": config.get_env("KAKAO_CLIENT_ID"),
            "redirect_uri": _callback_redirect_uri(request),
            "response_type": "code",
        }
    )
    return RedirectResponse(url=kakao_oauth_url, status_code=302)


@router.get("/callback")
async def callback(request: Request, code: str):
    try:
        access_token = await KakaoAuthService.fetch_access_token(
            code,
            config.get_env("KAKAO_CLIENT_ID"),
            _callback_redirect_uri(request),
            config.get_env("KAKAO_CLIENT_SECRET"),
        )
        user_info = await KakaoAuthService.fetch_user_info(access_token, "kakao")
        if user_info is None:
            raise HTTPException(status_code=502, detail="failed_to_fetch_kakao_user")

        refresh_token = JWTService.create_refresh_token(user_info.user_id, "kakao")
        UserService.save_user_to_db(user_info, refresh_token)
        jwt_token = JWTService.create_access_token(user_info.user_id, "kakao")

        response = RedirectResponse(url=config.get_env("WEBSITE_URL"), status_code=302)
        _set_session_cookies(response, jwt_token, refresh_token)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/auth/refresh")
def refresh_session(request: Request) -> Response:
    refresh_token = request.cookies.get("refresh_token")
    tokens = UserService.rotate_session(refresh_token) if refresh_token else None
    if tokens is None:
        return JSONResponse(status_code=401, content={"detail": "invalid_refresh_token"})

    access_token, next_refresh_token = tokens
    response = Response(status_code=204)
    _set_session_cookies(response, access_token, next_refresh_token)
    return response
