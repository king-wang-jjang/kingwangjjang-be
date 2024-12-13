from authlib.integrations.starlette_client import OAuth
from app.config import Config
import jwt
import hashlib
from datetime import datetime,timedelta
from app.utils.loghandler import catch_exception,setup_logger
import sys
sys.excepthook = catch_exception
logger = setup_logger()
oauth = OAuth()

# Google API용 OAuth 2.0 인증 정보
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
]

oauth.register(
    name="google",
    client_id=Config().get_env("GOOGLE_CLIENT_ID"),
    client_secret=Config().get_env("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="kakao",
    client_id=Config().get_env("KAKAO_CLIENT_ID"),
    server_metadata_url="https://kauth.kakao.com/.well-known/openid-configuration",
    client_kwargs={"scope": "profile_nickname"},
)


class JWT():
    def __init__(self):
        self.secret_key = Config().get_env("JWT_SECRET_KEY")
        logger.info(f"JWT secret key: {self.secret_key}")
    def encode(self, payload):
        logger.debug(f"JWT encode payload: {payload}, type: {type(payload)}")
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def decode(self, token):
        logger.debug(f"JWT decode token: {token}, type: {type(token)}")
        return jwt.decode(token, self.secret_key, algorithms=['HS256'])
