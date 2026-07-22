from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.admin_access import resolve_user_role
from app.services.token_service import TokenDecodeError, TokenService
from app.utils.loghandler import setup_logger


logger = setup_logger()


class AuthMiddleware(BaseHTTPMiddleware):
    """Optional edge authentication for downstream services.

    The gateway only verifies the access token and forwards trusted identity
    headers. OAuth, refresh tokens, and user persistence belong to user-service.
    """

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("access_token")

        if not token:
            request.state.auth_status = "unauthenticated"
            request.state.auth_error = "no_token"
            return await call_next(request)

        try:
            user_id, auth_provider = self._authenticate_token(token)
            request.state.user_id = user_id
            request.state.auth_provider = auth_provider
            request.state.user_role = resolve_user_role(user_id)
            request.state.auth_status = "authenticated"
            if hasattr(request.state, "auth_error"):
                delattr(request.state, "auth_error")
            logger.info("Authenticated user: %s with provider: %s", user_id, auth_provider)
        except HTTPException as exc:
            request.state.auth_status = "unauthenticated"
            request.state.auth_error = self._auth_error_code(exc)
            logger.warning("Authentication failed: %s", exc.detail)
        except Exception as exc:
            request.state.auth_status = "unauthenticated"
            request.state.auth_error = "internal_auth_error"
            logger.error("Authentication error: %s", exc)

        return await call_next(request)

    def _authenticate_token(self, token: str) -> tuple[str, str]:
        try:
            decoded_payload = TokenService.decode_access_token(token)
        except TokenDecodeError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

        user_id = decoded_payload.get("user_id")
        auth_provider = decoded_payload.get("auth_provider")

        if user_id is None:
            raise HTTPException(status_code=403, detail="invalid_token")

        return str(user_id), str(auth_provider)

    @staticmethod
    def _auth_error_code(exc: HTTPException) -> str:
        detail = str(exc.detail) if exc.detail else "auth_error"
        if exc.status_code == 401:
            return "token_expired"
        if exc.status_code == 403 and detail == "invalid_token":
            return "invalid_token"
        if exc.status_code == 403:
            return "forbidden"
        return detail


class UserInfoMiddleware(BaseHTTPMiddleware):
    """Retained for compatibility; proxy routing injects trusted headers."""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    """Retained for middleware order compatibility.

    Access token refresh is intentionally owned by user-service, not gateway.
    """

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
