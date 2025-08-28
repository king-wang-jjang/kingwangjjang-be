from fastapi.responses import RedirectResponse
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
import sys

from app.utils.loghandler import Config
from app.services.auth_services import JWTService
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
            "user/": "localhost:33334",
            "commentservice/": "localhost:33335",
        }
    for prefix, target in service_map.items():
        if path.startswith(prefix):
            return f"http://{target}/{path[len(prefix):]}"
    return ""


def authenticate_user_request(request: Request) -> str:
    """JWT 검증 및 user_id 추출"""
    is_graphql_generate = config.get_env('SERVER_TYPE')
    if (is_graphql_generate == "GRAPHQL-GENERATE"):
        logger.info(f"Skip Authenticate (is_graphql_generate): {is_graphql_generate}")
        return 3891969863
    
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("Unauthorized access attempt: Missing token")
        raise HTTPException(status_code=403, detail="Access forbidden: Missing token")

    decoded_token = JWTService.decode_access_token(access_token=token)
    user_id = decoded_token if decoded_token else None

    if not user_id:
        logger.warning(f"Invalid token access attempt: {token}")
        raise HTTPException(status_code=403, detail="Access forbidden: Invalid token")
    
    return user_id

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    url = get_service_url(path)
    if not url:
        raise HTTPException(status_code=404, detail="Invalid path prefix")
    
    user_id = None
    if path.startswith("user/"):
        user_id = authenticate_user_request(request)

    try:
        async with httpx.AsyncClient() as client:
            headers = dict(request.headers)
            
            # 🔹 User-Service 요청 시 `user_id`를 Header에 추가
            if user_id:
                headers["X-User-Id"] = str(user_id)
                logger.info(f"Forwarding request to User-Service with X-User-Id: {user_id}")

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
