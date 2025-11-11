from fastapi import HTTPException
from app.utils.oauth import JWT

def get_authenticated_user_id(info) -> str:
    """
    GraphQL Info에서 요청 컨텍스트를 통해 인증된 사용자 ID를 반환.
    - 우선 게이트웨이가 추가한 X-User-Id 헤더를 사용
    - 없으면 쿠키의 access_token(JWT)에서 user_id를 추출
    - 둘 다 없으면 401
    """
    request = info.context.get("request") if hasattr(info, "context") else None
    if request is None:
        raise HTTPException(status_code=500, detail="missing_request_context")

    user_id = request.headers.get("X-User-Id") or request.headers.get("x-user-id")
    if not user_id:
        token = request.cookies.get("access_token")
        if token:
            try:
                payload = JWT().decode(token)
                user_id = str(payload.get("user_id"))
            except Exception:
                user_id = None

    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")

    return str(user_id)


