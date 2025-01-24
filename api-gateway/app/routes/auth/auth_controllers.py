import sys
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from dotenv import load_dotenv
from app.config import Config
from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception
from app.routes.auth.auth_models import KakaoUserInfo, MongoUser

sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()

KAKAO_CLIENT_ID = Config().get_env("KAKAO_CLIENT_ID")
REDIRECT_URI = Config().get_env("REDIRECT_URI")
KAKAO_CLIENT_SECRET = Config().get_env("KAKAO_CLIENT_SECRET")

class OAuthToken(BaseModel):
    access_token: str

@router.get("/login")
async def login():
    kakao_oauth_url = (
        f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    )
    
    return RedirectResponse(url=kakao_oauth_url)

@router.get("/callback")
async def callback(code: str):
    # 카카오에서 받은 인가 코드로 액세스 토큰 요청
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "client_secret": KAKAO_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
    access_token = response.json().get("access_token")
    
    # 액세스 토큰을 사용하여 사용자 정보 가져오기
    user_info_url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        user_response = await client.get(user_info_url, headers=headers)
    
    user_data = user_response.json()
    kakao_user = KakaoUserInfo(
        id=user_data["id"],
        email=user_data["kakao_account"].get("email"),
        nickname=user_data["properties"].get("nickname"),
        profile_image=user_data["properties"].get("profile_image")
    )
    
    return {"user_info": kakao_user}
