from typing import Optional
from fastapi import Request

def extract_user_info_from_context(info) -> tuple[Optional[str], Optional[str]]:
    """GraphQL Context에서 API Gateway로부터 전달받은 사용자 정보를 추출"""
    # Strawberry GraphQL에서 Request 객체 접근 방식
    request = info.context.get("request")
    if not request:
        return None, None
    
    # API Gateway에서 전달된 헤더에서 사용자 정보 추출
    user_id = request.headers.get("x-user-id") or request.headers.get("X-User-Id")
    auth_provider = request.headers.get("x-auth-provider") or request.headers.get("X-Auth-Provider")

    return user_id, auth_provider

def require_authenticated_user(info) -> str:
    """인증된 사용자만 허용하는 함수"""
    request = info.context.get("request")
    if not request:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="missing_request_context")

    # API Gateway에서 전달된 인증 상태 확인
    status = request.headers.get("X-Auth-Status") or request.headers.get("x-auth-status")
    if status != "authenticated":
        from fastapi import HTTPException
        err = request.headers.get("X-Auth-Error") or request.headers.get("x-auth-error") or "auth_required"
        if err in ("no_token", "token_expired", "invalid_token", "auth_required"):
            raise HTTPException(status_code=401, detail=err)
        raise HTTPException(status_code=403, detail=err)

    # 상태가 authenticated면 최소한 사용자 식별자가 있는지 확인
    user_id, _ = extract_user_info_from_context(info)
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="auth_required")
    return str(user_id)

def get_user_from_db(user_id: str, auth_provider: str) -> Optional[str]:
    """DB에서 실제 사용자 ID를 조회하여 반환"""
    try:
        from app.db.mongo_controller import MongoController
        db_controller = MongoController()
        
        # user_id와 auth_provider로 사용자 조회
        query_filter = {"user_id": int(user_id)}
        if auth_provider:
            query_filter["auth_provider"] = auth_provider
        
        user = db_controller.find_one("users", query_filter)
        if user:
            return str(user["_id"])  # MongoDB의 _id 반환
        return None
    except Exception as e:
        print(f"사용자 조회 실패: {e}")
        return None

def get_authenticated_user_id(info) -> str:
    """인증된 사용자의 DB 사용자 ID를 반환"""
    # 1. 인증 상태 확인
    user_id, auth_provider = extract_user_info_from_context(info)
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="auth_required")
    
    # 2. DB에서 실제 사용자 ID 조회
    db_user_id = get_user_from_db(user_id, auth_provider)
    if not db_user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="user_not_found")
    
    return db_user_id
