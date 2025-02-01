import strawberry
from app.graphql.resolvers import get_user_by_id
from app.models.auth_models import UserType

@strawberry.type
class UserQuery:
    @strawberry.field
    async def get_user(self, info, user_id: str) -> UserType:
        return await get_user_by_id(user_id)
