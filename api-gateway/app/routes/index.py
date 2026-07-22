import sys

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app.utils.loghandler import Config, catch_exception, setup_logger


sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()
config = Config()
PROXY_TIMEOUT_SECONDS = 90.0
TRUSTED_IDENTITY_HEADERS = (
    "X-User-Id",
    "X-Auth-Provider",
    "X-User-Role",
    "X-Auth-Status",
    "X-Auth-Error",
)


SERVER_SERVICE_MAP = {
    "boardservice/": "kingwangjjang-board-service:33333",
    "userservice/": "kingwangjjang-user-service:33334",
    "commentservice/": "kingwangjjang-comment-service:33335",
    "gptservice/": "kingwangjjang-gpt-service:33336",
}
LOCAL_SERVICE_MAP = {
    "boardservice/": "localhost:33333",
    "userservice/": "localhost:33334",
    "commentservice/": "localhost:33335",
    "gptservice/": "localhost:33336",
}
SERVER_AUTH_PATHS = {
    "login": "kingwangjjang-user-service:33334",
    "callback": "kingwangjjang-user-service:33334",
}
LOCAL_AUTH_PATHS = {
    "login": "localhost:33334",
    "callback": "localhost:33334",
}


def get_service_url(path: str) -> str:
    is_local = config.get_env("SERVER_RUN_MODE") == "FALSE"
    service_map = LOCAL_SERVICE_MAP if is_local else SERVER_SERVICE_MAP
    auth_paths = LOCAL_AUTH_PATHS if is_local else SERVER_AUTH_PATHS

    if path in auth_paths:
        return f"http://{auth_paths[path]}/{path}"

    for prefix, target in service_map.items():
        if path.startswith(prefix):
            return f"http://{target}/{path[len(prefix):]}"
    return ""


def _target_url_with_query(url: str, request: Request) -> str:
    if request.url.query:
        return f"{url}?{request.url.query}"
    return url


def _response_headers(response: httpx.Response) -> dict[str, str]:
    headers = dict(response.headers)
    headers.pop("transfer-encoding", None)
    headers.pop("content-encoding", None)
    headers.pop("content-length", None)
    headers.pop("set-cookie", None)
    return headers


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    url = get_service_url(path)
    if not url:
        raise HTTPException(status_code=404, detail="Invalid path prefix")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(PROXY_TIMEOUT_SECONDS)) as client:
            headers = dict(request.headers)
            for header_name in TRUSTED_IDENTITY_HEADERS:
                headers.pop(header_name, None)
                headers.pop(header_name.lower(), None)

            if hasattr(request.state, "user_id") and hasattr(request.state, "auth_provider"):
                headers["X-User-Id"] = str(request.state.user_id)
                headers["X-Auth-Provider"] = str(request.state.auth_provider)
                headers["X-User-Role"] = str(getattr(request.state, "user_role", "user"))

            headers["X-Auth-Status"] = str(getattr(request.state, "auth_status", "unauthenticated"))
            auth_error = getattr(request.state, "auth_error", None)
            if auth_error:
                headers["X-Auth-Error"] = str(auth_error)

            response = await client.request(
                method=request.method,
                url=_target_url_with_query(url, request),
                headers=headers,
                cookies=request.cookies,
                data=await request.body(),
            )

            proxied_response = Response(
                content=response.content,
                status_code=response.status_code,
                headers=_response_headers(response),
                media_type=response.headers.get("Content-Type"),
            )
            for cookie in response.headers.get_list("set-cookie"):
                proxied_response.headers.append("set-cookie", cookie)
            return proxied_response
    except Exception as exc:
        logger.error("Error forwarding request to %s: %s", url, exc)
        raise HTTPException(status_code=500, detail="Error forwarding request to proxy server") from exc
