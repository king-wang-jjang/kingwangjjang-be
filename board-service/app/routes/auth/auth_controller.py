from fastapi import FastAPI, APIRouter, HTTPException, Request
from app.services.user.user import get_user_by_email, add_user
from app.utils.oauth import oauth, JWT
from app.config import Config
from datetime import datetime, timedelta
import logging

# FastAPI 및 APIRouter 초기화
app = FastAPI()
router = APIRouter()

# 로거 설정
logger = logging.getLogger(__name__)

@router.get("/login/google")
async def login_via_google(request: Request):
    """
    Google로 로그인 요청을 보내는 엔드포인트.
    """
    try:
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            redirect_uri = "https://api.top1.kr/callback/google"
        else:
            redirect_uri = request.url_for('auth_via_google')
        logger.info("Redirecting to Google for authorization")
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error during Google login: {e}")
        raise HTTPException(status_code=500, detail="Error during Google login")

@router.get("/callback/google")
async def auth_via_google(request: Request):
    """
    Google에서 반환된 토큰을 처리하고 사용자 정보를 반환하는 엔드포인트.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token['userinfo']

        # 사용자 정보를 데이터베이스에서 검색
        user_data = get_user_by_email(user_info["email"])

        if user_data:
            # 사용자 존재 시 JWT 토큰 생성
            user_data["_id"] = str(user_data["_id"])
            user_data["exp"] = datetime.utcnow() + timedelta(days=3)
            user_data["jwt"] = JWT().encode(user_data)
            logger.info(f"User {user_info['email']} logged in successfully")
            return user_data
        else:
            # 신규 사용자 추가
            add_user(user_info["email"], user_info["name"])
            user_data = get_user_by_email(user_info["email"])
            user_data["_id"] = str(user_data["_id"])
            user_data["jwt"] = JWT().encode(user_data)
            logger.info(f"New user {user_info['email']} added and logged in successfully")
            return user_data

    except Exception as e:
        logger.error(f"Error during Google callback: {e}")
        raise HTTPException(status_code=500, detail="Error during Google callback")
