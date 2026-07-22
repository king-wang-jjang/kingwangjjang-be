from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_optional_principal
from app.auth.principal import Principal
from app.repositories.users import UserRepository


router = APIRouter(prefix="/api/users", tags=["users"])


class UpdateMeRequest(BaseModel):
    displayName: str | None = None


def _to_me_response(user: dict, role: str = "user") -> dict:
    return {
        "Id": user["id"],
        "userId": user["user_id"],
        "nickname": user.get("nickname"),
        "displayName": user.get("display_name"),
        "authProvider": user["auth_provider"],
        "profileImage": user.get("profile_image"),
        "createTime": user["created_at"],
        "role": "admin" if role == "admin" else "user",
    }


@router.get("/me")
def me(principal: Principal = Depends(get_optional_principal)):
    if not principal.is_authenticated:
        return None

    user = UserRepository().get_or_create_from_principal(principal)
    return _to_me_response(user, principal.role)


@router.patch("/me")
def update_me(payload: UpdateMeRequest, principal: Principal = Depends(get_optional_principal)):
    if not principal.is_authenticated:
        raise HTTPException(status_code=401, detail="authentication_required")

    display_name = payload.displayName.strip() if payload.displayName is not None else None
    if display_name == "":
        display_name = None

    if display_name is not None and len(display_name) > 40:
        raise HTTPException(status_code=422, detail="displayName must be 40 characters or fewer")

    user = UserRepository().update_display_name_from_principal(principal, display_name)
    return _to_me_response(user, principal.role)
