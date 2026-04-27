import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.config import Config
from app.services.auth_service import JWTService, KakaoAuthService, UserService


router = APIRouter()
config = Config()


def _cookie_secure() -> bool:
    return os.getenv("AUTH_COOKIE_SECURE", "TRUE").upper() not in {"0", "FALSE", "NO"}


@router.get("/login")
def login():
    kakao_oauth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={config.get_env('KAKAO_CLIENT_ID')}"
        f"&redirect_uri={config.get_env('REDIRECT_URI')}"
        "&response_type=code"
    )
    return RedirectResponse(url=kakao_oauth_url, status_code=302)


@router.get("/callback")
async def callback(code: str):
    try:
        access_token = await KakaoAuthService.fetch_access_token(
            code,
            config.get_env("KAKAO_CLIENT_ID"),
            config.get_env("REDIRECT_URI"),
            config.get_env("KAKAO_CLIENT_SECRET"),
        )
        user_info = await KakaoAuthService.fetch_user_info(access_token, "kakao")
        if user_info is None:
            raise HTTPException(status_code=502, detail="failed_to_fetch_kakao_user")

        refresh_token = JWTService.create_refresh_token(user_info.user_id, "kakao")
        UserService.save_user_to_db(user_info, refresh_token)
        jwt_token = JWTService.create_access_token(user_info.user_id, "kakao")

        response = RedirectResponse(url=config.get_env("WEBSITE_URL"), status_code=302)
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=_cookie_secure(),
            samesite="lax",
            max_age=3600,
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
