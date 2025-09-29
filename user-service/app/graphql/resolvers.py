from typing import Optional
from app.db.mongo_controller import MongoController
from app.models.auth_models import UserType
from app.utils.jwt_handler import get_current_user_from_request, get_current_user_info_from_request
from fastapi import Request, HTTPException
from strawberry.types import Info  

mongo = MongoController()

def extract_user_info_from_context(info: Info) -> tuple[Optional[str], Optional[str]]:
    """GraphQL Context에서 user_id와 auth_provider를 추출 (JWT 토큰 우선, 헤더 대체)"""
    # Strawberry GraphQL에서 Request 객체 접근 방식
    request = info.context.get("request")
    if not request:
        return None, None
    
    # 1. JWT 토큰에서 사용자 정보 추출 시도 (쿠키 또는 헤더)
    user_id, auth_provider = get_current_user_info_from_request(request)
    if user_id:
        return user_id, auth_provider
    
    # 2. JWT 토큰이 없으면 기존 헤더 방식 사용
    user_id = request.headers.get("x-user-id") or request.headers.get("X-User-Id")
    auth_provider = request.headers.get("x-auth-provider") or request.headers.get("X-Auth-Provider")

    return user_id, auth_provider

async def get_user_by_id(info: Info, id: Optional[str] = None) -> Optional[UserType]:
    """user_id가 없을 경우, Context에서 추출하고 auth_provider로 필터링"""
    if id is None or id == '':
        user_id, auth_provider = extract_user_info_from_context(info)  # 🔹 GraphQL Context에서 user_id와 auth_provider 가져오기
    else:
        # id가 제공된 경우, auth_provider만 헤더에서 추출
        request = info.context.get("request")
        auth_provider = None
        if request:
            auth_provider = request.headers.get("x-auth-provider") or request.headers.get("X-Auth-Provider")
        user_id = id
    
    if user_id is None:
        return None
    
    # auth_provider로 필터링하여 사용자 조회
    query_filter = {"user_id": int(user_id)}
    if auth_provider:
        query_filter["auth_provider"] = auth_provider
    
    user = mongo.find_user(query_filter)  # MongoDB에서 auth_provider와 함께 조회

    if user:
        user_data = {k: v for k, v in user.items() if k in UserType.__annotations__}  
        return UserType(**user_data)
    return None

def require_authenticated_user(info: Info) -> str:
    """게이트웨이 헤더를 기준으로 인증을 강제. 실패 시 적절한 상태코드/에러명으로 예외 발생"""
    request = info.context.get("request")
    if not request:
        raise HTTPException(status_code=500, detail="missing_request_context")

    status = request.headers.get("X-Auth-Status") or request.headers.get("x-auth-status")
    if status != "authenticated":
        err = request.headers.get("X-Auth-Error") or request.headers.get("x-auth-error") or "auth_required"
        if err in ("no_token", "token_expired", "invalid_token", "auth_required"):
            raise HTTPException(status_code=401, detail=err)
        raise HTTPException(status_code=403, detail=err)

    # 상태가 authenticated면 최소한 사용자 식별자가 있는지 확인
    user_id, _ = extract_user_info_from_context(info)
    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")
    return str(user_id)