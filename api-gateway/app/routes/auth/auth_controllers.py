from dataclasses import asdict
import datetime
import sys
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.models.auth_models import UserType
from app.db.mongo_controller import MongoController
from app.config import Config
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.services.auth_services import JWTService, KakaoAuthService, UserService
from app.utils.loghandler import catch_exception, setup_logger

sys.excepthook = catch_exception
logger = setup_logger()

config = Config()
KAKAO_API_BASE = "https://kapi.kakao.com"
db_controller = MongoController()
router = APIRouter()

KAKAO_CLIENT_ID = config.get_env("KAKAO_CLIENT_ID")
REDIRECT_URI = config.get_env("REDIRECT_URI")
KAKAO_CLIENT_SECRET = config.get_env("KAKAO_CLIENT_SECRET")
WEBSITE_URL = config.get_env("WEBSITE_URL")

class KakaoAuthService:
    @staticmethod
    async def fetch_access_token(code: str, client_id: str, redirect_uri: str, client_secret: str):
        """카카오에서 Access Token 가져오기"""
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
        
        return token_data.get("access_token")
    
    @staticmethod
    async def fetch_user_info(access_token: str) -> UserType:
        """Access Token으로 카카오 사용자 정보 가져오기"""
        user_info_url = f"{KAKAO_API_BASE}/v2/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            user_data = response.json()

        return UserType(
            user_id=user_data["id"]
        )

@router.get("/login")
def login():
    """카카오 로그인 URL로 리다이렉션"""
    kakao_oauth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    )
    return RedirectResponse(url=kakao_oauth_url, status_code=302)

@router.get("/callback")
async def callback(code: str):
    try:
        access_token = await KakaoAuthService.fetch_access_token(
            code, KAKAO_CLIENT_ID, REDIRECT_URI, KAKAO_CLIENT_SECRET
        )
        user_info = await KakaoAuthService.fetch_user_info(access_token)
        refresh_token = JWTService.create_refresh_token(user_info.user_id)
        
        # refresh_token을 DB에 저장
        await UserService.save_user_to_db(user_info, refresh_token)
        
        jwt_token = JWTService.create_access_token(user_info.user_id)
        
        JWTService.decode_access_token(access_token=jwt_token)

        response = RedirectResponse(url=WEBSITE_URL, status_code=302)
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=3600,
        )
        
        return response  # refresh_token은 쿠키에서 제거하고 서버에서만 관리
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))