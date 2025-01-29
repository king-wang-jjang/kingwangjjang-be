from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.config import Config
from app.services.auth_services import KakaoAuthService, UserService

router = APIRouter()
config = Config()

KAKAO_CLIENT_ID = config.get_env("KAKAO_CLIENT_ID")
REDIRECT_URI = config.get_env("REDIRECT_URI")
KAKAO_CLIENT_SECRET = config.get_env("KAKAO_CLIENT_SECRET")

@router.get("/login")
def login():
    """카카오 로그인 URL로 리다이렉션"""
    kakao_oauth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    )
    return RedirectResponse(url=kakao_oauth_url)

@router.get("/callback")
async def callback(code: str):
    """카카오 인증 후 콜백 처리"""
    try:
        # 1. Access Token 요청
        access_token = await KakaoAuthService.fetch_access_token(
            code, KAKAO_CLIENT_ID, REDIRECT_URI, KAKAO_CLIENT_SECRET
        )
        # 2. 사용자 정보 요청
        user_info = await KakaoAuthService.fetch_user_info(access_token)
        # 3. 사용자 정보를 DB에 저장
        user = await UserService.save_user_to_db(user_info)
        return {"message": "Login successful", "user": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
