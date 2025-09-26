from typing import Optional
import strawberry
from app.graphql.resolvers import get_user_by_id
from app.models.auth_models import UserType
from strawberry.types import Info  

@strawberry.type
class UserQuery:
    @strawberry.field
    async def get_user(self, info: Info, user_id: Optional[str] = None) -> Optional[UserType]:
        return await get_user_by_id(info, user_id)
    
    @strawberry.field
    async def me(self, info: Info) -> Optional[UserType]:
        # 현재 인증된 사용자 정보를 반환
        # JWT 토큰에서 사용자 ID를 추출하여 사용자 정보 조회
        return await get_user_by_id(info, None)  # None을 전달하면 자동으로 context에서 사용자 ID 추출