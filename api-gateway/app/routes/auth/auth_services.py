import httpx
from app.routes.auth.auth_models import UserInfo
from app.db.mongo_controller import MongoController


KAKAO_API_BASE = "https://kapi.kakao.com"
db_controller = MongoController()
class AuthService:
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
            response.raise_for_status()  # 에러 발생 시 예외 처리
            return response.json().get("access_token")

    @staticmethod
    async def fetch_user_info(access_token: str) -> UserInfo:
        """Access Token으로 카카오 사용자 정보 가져오기"""
        user_info_url = f"{KAKAO_API_BASE}/v2/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()  # 에러 발생 시 예외 처리
            user_data = response.json()

        return UserInfo(
            id=user_data["id"]
        )

    @staticmethod
    async def save_user_to_db(user_info: UserInfo):
        """사용자 정보를 MongoDB에 저장"""
        existing_user = db_controller.find_user({"id": user_info.id})
        if existing_user:
            return existing_user
        else:
            db_controller.insert_user(user_info.dict())
            return user_info.dict()
