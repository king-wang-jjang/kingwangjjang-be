import os


ADMIN_ROLE = "admin"
USER_ROLE = "user"


def configured_admin_user_ids(raw_value: str | None = None) -> set[str]:
    value = os.getenv("ADMIN_USER_IDS", "") if raw_value is None else raw_value
    return {user_id.strip() for user_id in value.split(",") if user_id.strip()}


def resolve_user_role(user_id: str | None, raw_value: str | None = None) -> str:
    if not user_id:
        return USER_ROLE
    if str(user_id) in configured_admin_user_ids(raw_value):
        return ADMIN_ROLE
    return USER_ROLE
