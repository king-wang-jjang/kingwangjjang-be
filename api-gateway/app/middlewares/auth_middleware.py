from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.services.auth_services import JWTService
from app.utils.loghandler import setup_logger
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

logger = setup_logger()

class AuthMiddleware(BaseHTTPMiddleware):
    """인증 미들웨어 - JWT 토큰 검증 및 사용자 정보 추출 (선택적 인증)"""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """미들웨어 처리 로직 - 선택적 인증"""
        
        # 모든 경로에서 동일한 선택적 인증을 수행합니다.
        
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
                request.state.auth_status = "authenticated"
                # 이전 에러 상태가 있었다면 초기화
                if hasattr(request.state, 'auth_error'):
                    delattr(request.state, 'auth_error')
                
                # 새 토큰이 발급된 경우 저장
                if new_token:
                    request.state.new_access_token = new_token
                
                logger.info(f"Authenticated user: {user_id} with provider: {auth_provider}")
            else:
                # 인증이 선택적이면 토큰 없이 진행
                request.state.auth_status = "unauthenticated"
                request.state.auth_error = "no_token"
                logger.info("No token provided, proceeding without authentication")
            
        except HTTPException as e:
            # 인증 실패 시 요청은 계속 진행하되 상태/에러 정보를 기록
            request.state.auth_status = "unauthenticated"
            # 에러명을 표준화하여 다운스트림 서비스로 전달
            detail = str(e.detail) if hasattr(e, 'detail') else "auth_error"
            if e.status_code == 401:
                request.state.auth_error = "token_expired"
            elif e.status_code == 403:
                if "Invalid token" in detail:
                    request.state.auth_error = "invalid_token"
                else:
                    request.state.auth_error = "forbidden"
            else:
                request.state.auth_error = "auth_error"
            logger.warning(f"Authentication failed, skipping auth: {detail}")
        except Exception as e:
            # 예상치 못한 에러 - 요청은 계속 진행하되 에러 코드만 기록
            request.state.auth_status = "unauthenticated"
            request.state.auth_error = "internal_auth_error"
            logger.error(f"Authentication error, skipping auth: {e}")
        
        # 다음 미들웨어/라우터로 전달
        response = await call_next(request)
        return response
    
    def _authenticate_request(self, request: Request) -> tuple[str, str, str]:
        """JWT 토큰 검증 및 사용자 정보 추출 (자동 재발급 포함)"""
        # 쿠키에서 토큰 추출 (auth_provider는 토큰에서 추출)
        token = request.cookies.get("access_token")
        
        if not token:
            logger.warning("Unauthorized access attempt: Missing token")
            raise HTTPException(status_code=403, detail="Access forbidden: Missing token")
        
        # JWT 토큰 만료만 검증 (자동 재발급 제거)
        try:
            decoded_payload = jwt.decode(token, JWTService.SECRET_KEY, algorithms=["HS256"])
        except ExpiredSignatureError:
            logger.warning("Access Token expired")
            raise HTTPException(status_code=401, detail="Access token expired")
        except InvalidTokenError:
            logger.warning("Invalid access token")
            raise HTTPException(status_code=403, detail="Access forbidden: Invalid token")

        user_id = decoded_payload.get("user_id")
        auth_provider = decoded_payload.get("auth_provider")

        if user_id is None:
            raise HTTPException(status_code=403, detail="Access forbidden: Invalid token")

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
