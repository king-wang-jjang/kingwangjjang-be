from fastapi import APIRouter, Depends

from app.auth.dependencies import get_optional_principal
from app.auth.principal import Principal
from app.repositories.users import UserRepository


router = APIRouter(prefix="/api/users", tags=["users"])


def _to_me_response(user: dict) -> dict:
    return {
        "Id": user["id"],
        "userId": user["user_id"],
        "nickname": user.get("nickname"),
        "authProvider": user["auth_provider"],
        "profileImage": user.get("profile_image"),
        "createTime": user["created_at"],
    }


@router.get("/me")
def me(principal: Principal = Depends(get_optional_principal)):
    if not principal.is_authenticated:
        return None

    user = UserRepository().get_or_create_from_principal(principal)
    return _to_me_response(user)
