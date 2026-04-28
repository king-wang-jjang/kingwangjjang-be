from fastapi import HTTPException, Request, status

from app.auth.principal import Principal


def get_optional_principal(request: Request) -> Principal:
    auth_status = request.headers.get("X-Auth-Status", "unauthenticated")
    user_id = request.headers.get("X-User-Id")
    auth_provider = request.headers.get("X-Auth-Provider")
    is_authenticated = auth_status == "authenticated" and bool(user_id)
    return Principal(user_id=user_id, auth_provider=auth_provider, is_authenticated=is_authenticated)


def require_principal(request: Request) -> Principal:
    principal = get_optional_principal(request)
    if not principal.is_authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return principal
