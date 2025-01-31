import strawberry
from app.db.mongo_controller import MongoController
from app.models.auth_models import UserType
from datetime import datetime

mongo = MongoController()

@strawberry.type
class UserMutation:
    @strawberry.mutation
    async def create_user(self, info, auth_organization: str, user_id: int, nickname: str, profile_image: str) -> UserType:
        user_data = UserType(
            id=user_id,
            auth_organization=auth_organization,
            nickname=nickname,
            profile_image=profile_image,
            create_time=datetime.utcnow()
        )

        # 기존 사용자 확인 후 저장
        existing_user = mongo.find_user({"id": user_id})
        if not existing_user:
            mongo.insert_user(user_data.dict())

        return user_data
