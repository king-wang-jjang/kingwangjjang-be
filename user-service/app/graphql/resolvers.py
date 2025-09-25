from typing import Optional
from app.db.mongo_controller import MongoController
from app.models.auth_models import UserType
from app.utils.jwt_handler import get_current_user_from_request, get_current_user_info_from_request
from fastapi import Request
from strawberry.types import Info  

mongo = MongoController()

def extract_user_info_from_context(info: Info) -> tuple[Optional[str], Optional[str]]:
    """GraphQL Context에서 user_id와 auth_provider를 추출 (JWT 토큰 우선, 헤더 대체)"""
    request: Request = info.context.get("request")  # FastAPI의 Request 객체 가져오기
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
        request: Request = info.context.get("request")
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