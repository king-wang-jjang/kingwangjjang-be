from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.services.auth_services import JWTService
from app.utils.loghandler import setup_logger

logger = setup_logger()

class AuthMiddleware(BaseHTTPMiddleware):
    """인증 미들웨어 - JWT 토큰 검증 및 사용자 정보 추출 (선택적 인증)"""
    
    def __init__(self, app, skip_paths: list = None, require_auth_paths: list = None):
        super().__init__(app)
        # 인증을 건너뛸 경로들 (예: 정적 파일, 헬스체크 등)
        self.skip_paths = skip_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/logout",
            "/static",
            # 공개 API 경로들
            "/boardservice/",  # 게시판 조회는 공개
            "/commentservice/",  # 댓글 조회는 공개
            "/userservice/public"  # 공개 사용자 정보
        ]
        # 인증이 필수인 경로들 (명시적으로 지정된 경로만)
        self.require_auth_paths = require_auth_paths or [
            "/userservice/me",
            "/userservice/profile",
            "/userservice/update",
            "/userservice/delete",
            "/boardservice/create",
            "/boardservice/update", 
            "/boardservice/delete",
            "/boardservice/like",
            "/boardservice/unlike",
            "/commentservice/create",
            "/commentservice/update",
            "/commentservice/delete"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """미들웨어 처리 로직 - 선택적 인증"""
        
        # 인증을 건너뛸 경로인지 확인
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # 인증이 필수인 경로인지 확인
        requires_auth = self._requires_auth(request.url.path)
        
        try:
            # 토큰이 있는지 확인 (선택적)
            token = request.cookies.get("access_token")
            
            if token:
                # 토큰이 있으면 검증하고 사용자 정보 추출 (자동 재발급 포함)
                auth_result = self._authenticate_request(request)
                user_id, auth_provider, new_token = auth_result
                
                # 요청에 사용자 정보 추가
                request.state.user_id = user_id
                request.state.auth_provider = auth_provider
                
                # 새 토큰이 발급된 경우 저장
                if new_token:
                    request.state.new_access_token = new_token
                
                logger.info(f"Authenticated user: {user_id} with provider: {auth_provider}")
            else:
                # 토큰이 없으면 인증이 필수인지 확인
                if requires_auth:
                    logger.warning("Unauthorized access attempt: Missing token for required auth path")
                    return Response(
                        content='{"detail": "Access forbidden: Authentication required"}',
                        status_code=401,
                        media_type="application/json"
                    )
                else:
                    # 인증이 선택적이면 토큰 없이 진행
                    logger.info("No token provided, proceeding without authentication")
            
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
    
    def _requires_auth(self, path: str) -> bool:
        """인증이 필수인 경로인지 확인"""
        return any(path.startswith(auth_path) for auth_path in self.require_auth_paths)
    
    def _authenticate_request(self, request: Request) -> tuple[str, str, str]:
        """JWT 토큰 검증 및 사용자 정보 추출 (자동 재발급 포함)"""
        # 쿠키에서 토큰 추출 (auth_provider는 토큰에서 추출)
        token = request.cookies.get("access_token")
        
        if not token:
            logger.warning("Unauthorized access attempt: Missing token")
            raise HTTPException(status_code=403, detail="Access forbidden: Missing token")
        
        # JWT 토큰 검증 (자동 재발급 포함)
        decoded_result = JWTService.decode_access_token(access_token=token)
        
        if not decoded_result:
            logger.warning(f"Invalid token access attempt: {token}")
            raise HTTPException(status_code=403, detail="Access forbidden: Invalid token")
        
        # 자동 재발급된 경우 처리
        if isinstance(decoded_result, dict) and "new_token" in decoded_result:
            user_id = decoded_result["user_id"]
            new_token = decoded_result["new_token"]
            auth_provider = decoded_result["auth_provider"]
            
            # 새 토큰을 request.state에 저장하여 응답에서 설정할 수 있도록 함
            request.state.new_access_token = new_token
            request.state.new_auth_provider = auth_provider
            
            logger.info(f"새로운 Access Token이 발급되었습니다: user_id={user_id}")
            return str(user_id), str(auth_provider), new_token
        
        # 정상적인 토큰인 경우
        user_id = decoded_result["user_id"]
        auth_provider = decoded_result["auth_provider"]
        return str(user_id), str(auth_provider), ""

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

class TokenRefreshMiddleware(BaseHTTPMiddleware):
    """새로 발급된 토큰을 쿠키에 설정하는 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        """새로 발급된 토큰을 응답 쿠키에 설정"""
        
        response = await call_next(request)
        
        # 새로 발급된 토큰이 있으면 쿠키에 설정
        if hasattr(request.state, 'new_access_token'):
            new_token = request.state.new_access_token
            new_auth_provider = getattr(request.state, 'new_auth_provider', None)
            
            # 새 Access Token을 쿠키에 설정
            response.set_cookie(
                key="access_token",
                value=new_token,
                httponly=True,
                secure=True,  # HTTPS에서만 전송
                samesite="lax",
                max_age=3600  # 1시간
            )
            
            # auth_provider도 업데이트
            if new_auth_provider:
                response.set_cookie(
                    key="auth_provider", 
                    value=new_auth_provider,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=3600
                )
            
            logger.info("새로운 Access Token이 쿠키에 설정되었습니다.")
        
        return response
