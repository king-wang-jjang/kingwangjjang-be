from app.db.mongo_controller import MongoController
from app.models.auth_models import UserType
from bson import ObjectId

mongo = MongoController()

async def get_user_by_id(id: str) -> UserType:
    user = mongo.find_user({"user_id": int(id)})  # MongoDB에서 id를 int로 저장

    if user:
        return UserType(**user)
    return None
 