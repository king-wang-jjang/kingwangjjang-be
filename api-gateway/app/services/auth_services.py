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
# Global exception handler and logger setup

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
            response.raise_for_status()  # 에러 발생 시 예외 처리
            return response.json().get("access_token")

    @staticmethod
    async def fetch_user_info(access_token: str) -> UserType:
        """Access Token으로 카카오 사용자 정보 가져오기"""
        user_info_url = f"{KAKAO_API_BASE}/v2/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()  # 에러 발생 시 예외 처리
            user_data = response.json()

        return UserType(
            user_id=user_data["id"]
        )

class UserService:
    @staticmethod
    async def save_user_to_db(user_info: UserType):
        """사용자 정보를 MongoDB에 저장"""
        existing_user = db_controller.find_user({"user_id": user_info.user_id})  # user_id가 아니라 id 필드 사용

        if existing_user:
            return existing_user
        else:
            # UserType 객체를 dict로 변환
            user_dict = asdict(user_info)
            db_controller.insert_user(user_dict)
            return user_dict  # MongoDB는 dict를 반환하는 것이 일반적
        
class JWTService:
    SECRET_KEY = config.get_env("JWT_SECRET_KEY")

    # JWT 생성 함수
    @classmethod
    def create_jwt(cls, user_id):

        payload = {
            "user_id": user_id,
            # 다른 OAuth 인증 기관을 추가하면 site 옵션을 추가해야한다.
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # 만료 시간
            "iat": datetime.datetime.utcnow(),  # 발급 시간
            "iss": "your-service-name",  # 발급자
        }
        token = jwt.encode(payload, cls.SECRET_KEY, algorithm="HS256")
        return token
        
    # JWT 검증 함수
    @classmethod
    def verify_jwt(cls, token):
        try:
            # 토큰 디코딩 및 검증
            decoded_payload = jwt.decode(token, cls.SECRET_KEY, algorithms=["HS256"])
            logger.info("검증 성공! Payload:", decoded_payload)
            return decoded_payload
        except ExpiredSignatureError:
            logger.warn("토큰이 만료되었습니다.")
        except InvalidTokenError:
            logger.error("유효하지 않은 토큰입니다.")