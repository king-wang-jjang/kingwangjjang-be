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