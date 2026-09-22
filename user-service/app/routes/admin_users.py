from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_validator

from app.auth.dependencies import configured_admin_user_ids, require_admin
from app.repositories.users import UserRepository
from app.routes.users import _to_me_response


router = APIRouter(
    prefix="/api/admin/users", tags=["admin-users"], dependencies=[Depends(require_admin)],
)


class UpdateAdminUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    displayName: str | None

    @field_validator("displayName")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        value = value.strip() or None if value is not None else None
        if value is not None and len(value) > 40:
            raise ValueError("displayName must be 40 characters or fewer")
        return value


def _member_response(user: dict | None, admin_ids: set[str]) -> dict:
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    role = "admin" if user["user_id"] in admin_ids else "user"
    return _to_me_response(user, role)


@router.get("")
def list_users(
    q: str = Query(default="", max_length=100),
    role: Literal["admin", "user"] | None = None,
    page: int = Query(default=1, ge=1, le=1_000_000),
    pageSize: int = Query(default=20, ge=1, le=100),
):
    admin_ids = configured_admin_user_ids()
    users, total = UserRepository().list_users(
        query=q.strip(), role=role, admin_user_ids=admin_ids, page=page, page_size=pageSize,
    )
    return {
        "items": [_member_response(user, admin_ids) for user in users],
        "total": total, "page": page, "pageSize": pageSize,
    }


@router.get("/{member_id}")
def get_user(member_id: str):
    return _member_response(UserRepository().get_user_by_id(member_id), configured_admin_user_ids())


@router.patch("/{member_id}")
def update_user(member_id: str, payload: UpdateAdminUserRequest):
    user = UserRepository().update_user_display_name(member_id, payload.displayName)
    return _member_response(user, configured_admin_user_ids())
