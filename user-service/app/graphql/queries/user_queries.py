from typing import Optional
import strawberry
from app.graphql.resolvers import get_user_by_id, require_authenticated_user
from app.models.auth_models import UserType
from strawberry.types import Info  

@strawberry.type
class UserQuery:
    @strawberry.field
    async def get_user(self, info: Info, user_id: Optional[str] = None) -> Optional[UserType]:
        return await get_user_by_id(info, user_id)
    
    @strawberry.field
    async def me(self, info: Info) -> Optional[UserType]:
        # 인증 강제: 게이트웨이 헤더 기반으로 검증
        require_authenticated_user(info)
        # 인증 통과 시 현재 사용자 정보 반환
        return await get_user_by_id(info, None)