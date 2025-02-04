from typing import Optional
from app.db.mongo_controller import MongoController
from app.models.auth_models import UserType
from fastapi import Request
from strawberry.types import Info  

mongo = MongoController()

def extract_user_id_from_context(info: Info) -> Optional[str]:
    """GraphQL Context에서 user_id를 추출"""
    request: Request = info.context.get("request")  # FastAPI의 Request 객체 가져오기
    if not request:
        return None
    
    # 헤더 키를 소문자로 변환하여 검색 (대소문자 문제 방지)
    user_id = request.headers.get("x-user-id") or request.headers.get("X-User-Id")
    
    return user_id

async def get_user_by_id(info: Info, id: Optional[str] = None) -> Optional[UserType]:
    """user_id가 없을 경우, Context에서 추출"""
    if id is None or id == '':
        id = extract_user_id_from_context(info)  # 🔹 GraphQL Context에서 user_id 가져오기
    
    if id is None:
        return None
    
    user = mongo.find_user({"user_id": int(id)})  # MongoDB에서 id를 int로 저장

    if user:
        user_data = {k: v for k, v in user.items() if k in UserType.__annotations__}  
        return UserType(**user_data)
    return None