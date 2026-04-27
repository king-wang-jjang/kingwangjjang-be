import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.config import Config


class TokenDecodeError(Exception):
    def __init__(self, status_code: int, code: str):
        super().__init__(code)
        self.status_code = status_code
        self.code = code


class TokenService:
    @staticmethod
    def _secret_key() -> str:
        secret = Config().get_env("JWT_SECRET_KEY")
        if not secret:
            raise TokenDecodeError(500, "jwt_secret_missing")
        return secret

    @classmethod
    def decode_access_token(cls, token: str) -> dict:
        try:
            return jwt.decode(token, cls._secret_key(), algorithms=["HS256"])
        except ExpiredSignatureError as exc:
            raise TokenDecodeError(401, "token_expired") from exc
        except InvalidTokenError as exc:
            raise TokenDecodeError(403, "invalid_token") from exc
