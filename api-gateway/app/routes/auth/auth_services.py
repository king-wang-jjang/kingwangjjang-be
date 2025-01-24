import sys
from fastapi import APIRouter
import httpx
from app.routes.auth.auth_models import KakaoUserInfo, MongoUser
from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception

db = MongoController()

sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()

class KakaoOAuthService:
    @staticmethod
    async def get_access_token(code: str) -> str:
        # 카카오 API로부터 액세스 토큰 가져오기
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": os.getenv("KAKAO_CLIENT_ID"),
            "client_secret": os.getenv("KAKAO_CLIENT_SECRET"),
            "redirect_uri": os.getenv("KAKAO_REDIRECT_URI"),
            "code": code,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
        return response.json().get("access_token")

    @staticmethod
    async def get_user_info(access_token: str) -> KakaoUserInfo:
        # 카카오 API로 사용자 정보 가져오기
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            user_response = await client.get(user_info_url, headers=headers)
        user_data = user_response.json()

        return KakaoUserInfo(
            id=user_data["id"],
            email=user_data["kakao_account"].get("email"),
            nickname=user_data["properties"].get("nickname"),
            profile_image=user_data["properties"].get("profile_image"),
        )

class UserService:
    @staticmethod
    async def save_user(user: KakaoUserInfo) -> MongoUser:
        # MongoDB에 사용자 저장
        user_collection = db["users"]
        existing_user = await user_collection.find_one({"kakao_id": user.id})
        if existing_user:
            # 이미 존재하면 업데이트
            await user_collection.update_one(
                {"kakao_id": user.id},
                {"$set": user.dict(exclude={"id"})}
            )
        else:
            # 존재하지 않으면 삽입
            await user_collection.insert_one({
                "kakao_id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "profile_image": user.profile_image,
            })

        updated_user = await user_collection.find_one({"kakao_id": user.id})
        return MongoUser(**updated_user)

    @staticmethod
    async def get_user_by_kakao_id(kakao_id: int) -> MongoUser:
        # MongoDB에서 사용자 조회
        user_collection = db["users"]
        user = await user_collection.find_one({"kakao_id": kakao_id})
        if user:
            return MongoUser(**user)
        return None
