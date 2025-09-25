from fastapi.responses import RedirectResponse
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
import sys

from app.utils.loghandler import Config
# JWTService는 이제 AuthMiddleware에서 사용됩니다.
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()
config = Config()

def get_service_url(path: str) -> str:
    is_server = config.get_env('SERVER_RUN_MODE')
    service_map = {
        "boardservice/": "kingwangjjang-board-service:33333",
        "user/": "kingwangjjang-user-service:33334",
        "commentservice/": "kingwangjjang-comment-service:33335",
    }
    if is_server == "FALSE":
        service_map = {
            "boardservice/": "localhost:33333",
            "userservice/": "localhost:33334",
            "commentservice/": "localhost:33335",
        }
    for prefix, target in service_map.items():
        if path.startswith(prefix):
            return f"http://{target}/{path[len(prefix):]}"
    return ""


# 인증 로직은 이제 AuthMiddleware에서 처리됩니다.

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    url = get_service_url(path)
    if not url:
        raise HTTPException(status_code=404, detail="Invalid path prefix")

    try:
        async with httpx.AsyncClient() as client:
            headers = dict(request.headers)
            
            # 미들웨어에서 추가된 사용자 정보 헤더 사용
            if hasattr(request.state, 'user_id') and hasattr(request.state, 'auth_provider'):
                headers["X-User-Id"] = str(request.state.user_id)
                headers["X-Auth-Provider"] = str(request.state.auth_provider)
                logger.info(f"Forwarding request with X-User-Id: {request.state.user_id} and X-Auth-Provider: {request.state.auth_provider}")

            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                cookies=request.cookies,
                data=await request.body(),
            )

            if response.is_redirect:
                return RedirectResponse(url=response.headers["Location"], status_code=response.status_code)

            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=response.headers.get('Content-Type')
            )

    except Exception as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        raise HTTPException(status_code=500, detail="Error forwarding request to proxy server")
