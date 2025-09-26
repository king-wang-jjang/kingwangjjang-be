import jwt
from typing import Optional, Dict, Any
from fastapi import Request
import os
from dotenv import load_dotenv

load_dotenv()

# JWT 시크릿 키 (환경변수에서 가져오거나 기본값 사용)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = "HS256"

def extract_token_from_cookie(request: Request, cookie_name: str = "access_token") -> Optional[str]:
    """쿠키에서 JWT 토큰을 추출"""
    try:
        token = request.cookies.get(cookie_name)
        return token
    except Exception as e:
        print(f"쿠키에서 토큰 추출 실패: {e}")
        return None

def extract_token_from_header(request: Request, header_name: str = "Authorization") -> Optional[str]:
    """헤더에서 JWT 토큰을 추출 (Bearer 토큰)"""
    try:
        auth_header = request.headers.get(header_name)
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]
        return None
    except Exception as e:
        print(f"헤더에서 토큰 추출 실패: {e}")
        return None

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT 토큰을 검증하고 페이로드를 반환"""
    try:
        if not token:
            return None
            
        # JWT 토큰 디코딩
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("JWT 토큰이 만료되었습니다.")
        return None
    except jwt.InvalidTokenError:
        print("유효하지 않은 JWT 토큰입니다.")
        return None
    except Exception as e:
        print(f"JWT 토큰 검증 실패: {e}")
        return None

def get_user_id_from_token(token: str) -> Optional[str]:
    """JWT 토큰에서 사용자 ID를 추출"""
    payload = verify_jwt_token(token)
    if payload:
        # 토큰 페이로드에서 사용자 ID 추출 (필드명은 실제 토큰 구조에 맞게 수정)
        return payload.get("user_id") or payload.get("sub") or payload.get("id")
    return None

def get_auth_provider_from_token(token: str) -> Optional[str]:
    """JWT 토큰에서 auth_provider를 추출"""
    payload = verify_jwt_token(token)
    if payload:
        return payload.get("auth_provider")
    return None

def get_current_user_from_request(request: Request) -> Optional[str]:
    """요청에서 현재 사용자 ID를 추출 (쿠키 우선, 헤더 대체)"""
    # 1. 쿠키에서 토큰 추출 시도
    token = extract_token_from_cookie(request)
    
    # 2. 쿠키에 토큰이 없으면 헤더에서 추출 시도
    if not token:
        token = extract_token_from_header(request)
    
    # 3. 토큰이 있으면 사용자 ID 추출
    if token:
        return get_user_id_from_token(token)
    
    return None

def get_current_user_info_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    """요청에서 현재 사용자 ID와 auth_provider를 추출 (쿠키 우선, 헤더 대체)"""
    # 1. 쿠키에서 토큰 추출 시도
    token = extract_token_from_cookie(request)
    
    # 2. 쿠키에 토큰이 없으면 헤더에서 추출 시도
    if not token:
        token = extract_token_from_header(request)
    
    # 3. 토큰이 있으면 사용자 정보 추출
    if token:
        user_id = get_user_id_from_token(token)
        auth_provider = get_auth_provider_from_token(token)
        return user_id, auth_provider
    
    return None, None
