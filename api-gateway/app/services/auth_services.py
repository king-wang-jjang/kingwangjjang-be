from dataclasses import asdict
import datetime
import sys
import httpx
import jwt
from app.models.auth_models import UserType
from app.db.mongo_controller import MongoController
from app.config import Config
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.utils.loghandler import catch_exception, setup_logger

sys.excepthook = catch_exception
logger = setup_logger()

config = Config()
KAKAO_API_BASE = "https://kapi.kakao.com"
db_controller = MongoController()

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

class UserService:
    @staticmethod
    async def save_user_to_db(user_info: UserType, refresh_token: str):
        """사용자 정보를 MongoDB에 저장 및 Refresh Token 저장"""
        existing_user = db_controller.find_user({"user_id": user_info.user_id})

        if existing_user:
            db_controller.update_user({"user_id": user_info.user_id}, {"refresh_token": refresh_token})
            return existing_user
        else:
            user_dict = asdict(user_info)
            user_dict["refresh_token"] = refresh_token
            db_controller.insert_user(user_dict)
            return user_dict
        
class JWTService:
    SECRET_KEY = config.get_env("JWT_SECRET_KEY")
    REFRESH_SECRET_KEY = config.get_env("JWT_REFRESH_SECRET_KEY")

    @classmethod
    def create_access_token(cls, user_id):
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow(),
            "iss": "api-gateway",
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm="HS256")
    
    @classmethod
    def create_refresh_token(cls, user_id):
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
            "iat": datetime.datetime.utcnow(),
            "iss": "api-gateway",
        }
        return jwt.encode(payload, cls.REFRESH_SECRET_KEY, algorithm="HS256")
        
    @classmethod
    def verify_access_token(cls, token, user_id):
        try:
            decoded_payload = jwt.decode(token, cls.SECRET_KEY, algorithms=["HS256"])
            logger.debug("사용자 검증 성공", decoded_payload)
            return True
        except ExpiredSignatureError:
            logger.warn("Access Token이 만료되었습니다. Refresh Token을 사용하여 새 Access Token을 발급합니다.")
            return cls.refresh_access_token(user_id)
        except InvalidTokenError:
            logger.error("유효하지 않은 토큰입니다.")
            return False

    @classmethod
    def refresh_access_token(cls, user_id):
        """우리 서비스에서 발급한 Refresh Token으로 Access Token 재발급"""
        user = db_controller.find_user({"user_id": user_id})
        if user and "refresh_token" in user:
            try:
                jwt.decode(user["refresh_token"], cls.REFRESH_SECRET_KEY, algorithms=["HS256"])
                new_access_token = cls.create_access_token(user_id)
                return new_access_token
            except ExpiredSignatureError:
                logger.warn("Refresh Token이 만료되었습니다. 다시 로그인해야 합니다.")
                return None
        return None
    
    @classmethod
    def decode_access_token(cls, access_token):
        try:
            decoded_payload = jwt.decode(access_token, cls.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_payload.get("user_id")
            return user_id
        except jwt.ExpiredSignatureError:
            logger.warn("토큰이 만료되었습니다.")
            # return cls.refresh_access_token(user_id)
            return None
        except jwt.InvalidTokenError:
            logger.error("유효하지 않은 토큰입니다.")
            return None
