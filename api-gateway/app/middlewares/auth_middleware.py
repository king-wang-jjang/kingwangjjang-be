from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.services.auth_services import JWTService
from app.utils.loghandler import setup_logger

logger = setup_logger()

class AuthMiddleware(BaseHTTPMiddleware):
    """인증 미들웨어 - JWT 토큰 검증 및 사용자 정보 추출"""
    
    def __init__(self, app, skip_paths: list = None):
        super().__init__(app)
        # 인증을 건너뛸 경로들 (예: 정적 파일, 헬스체크 등)
        self.skip_paths = skip_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/static"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """미들웨어 처리 로직"""
        
        # 인증을 건너뛸 경로인지 확인
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        try:
            # JWT 토큰 검증 및 사용자 정보 추출
            user_id, auth_provider = self._authenticate_request(request)
            
            # 요청에 사용자 정보 추가
            request.state.user_id = user_id
            request.state.auth_provider = auth_provider
            
            logger.info(f"Authenticated user: {user_id} with provider: {auth_provider}")
            
        except HTTPException as e:
            # 인증 실패 시 에러 반환
            logger.warning(f"Authentication failed: {e.detail}")
            return Response(
                content=f'{{"detail": "{e.detail}"}}',
                status_code=e.status_code,
                media_type="application/json"
            )
        except Exception as e:
            # 예상치 못한 에러
            logger.error(f"Authentication error: {e}")
            return Response(
                content='{"detail": "Internal authentication error"}',
                status_code=500,
                media_type="application/json"
            )
        
        # 다음 미들웨어/라우터로 전달
        response = await call_next(request)
        return response
    
    def _should_skip_auth(self, path: str) -> bool:
        """인증을 건너뛸 경로인지 확인"""
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)
    
    def _authenticate_request(self, request: Request) -> tuple[str, str]:
        """JWT 토큰 검증 및 사용자 정보 추출"""
        # 쿠키에서 토큰과 auth_provider 추출
        token = request.cookies.get("access_token")
        auth_provider = request.cookies.get("auth_provider")
        
        if not token:
            logger.warning("Unauthorized access attempt: Missing token")
            raise HTTPException(status_code=403, detail="Access forbidden: Missing token")
        
        # JWT 토큰 검증
        decoded_token = JWTService.decode_access_token(
            access_token=token, 
            auth_provider=auth_provider
        )
        
        if not decoded_token:
            logger.warning(f"Invalid token access attempt: {token}")
            raise HTTPException(status_code=403, detail="Access forbidden: Invalid token")
        
        return str(decoded_token), str(auth_provider) if auth_provider else ""

class UserInfoMiddleware(BaseHTTPMiddleware):
    """사용자 정보를 헤더에 추가하는 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        """사용자 정보를 헤더에 추가"""
        
        # 인증된 사용자 정보가 있으면 헤더에 추가
        if hasattr(request.state, 'user_id') and hasattr(request.state, 'auth_provider'):
            # 기존 헤더에 사용자 정보 추가
            request.headers.__dict__["_list"].append(("X-User-Id", str(request.state.user_id)))
            request.headers.__dict__["_list"].append(("X-Auth-Provider", str(request.state.auth_provider)))
            
            logger.info(f"Added user headers - X-User-Id: {request.state.user_id}, X-Auth-Provider: {request.state.auth_provider}")
        
        response = await call_next(request)
        return response
