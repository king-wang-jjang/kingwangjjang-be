import logging
import httpx
import json
from fastapi import APIRouter, Request, Response, HTTPException
import sys

from app.utils.loghandler import catch_exception, setup_logger

# Global exception handler and logger setup
sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    url = ""
    is_graphql = False  # GraphQL 요청 여부 감지

    # prefix에 따라 포트 설정
    if path.startswith("boardservice/"):
        port = 33333
        path = path[len("boardservice/"):]
        url = f"http://localhost:{port}/{path}"
    elif path.startswith("schedulerapp/"):
        port = 8003
        path = path[len("schedulerapp/"):]
        url = f"http://localhost:{port}/{path}"
    elif path.startswith("auth/"):
        port = 33334
        path = path[len("auth/"):]
        url = f"http://localhost:{port}/{path}"
        logger.info(url)
    else:
        raise HTTPException(status_code=404, detail="Invalid path prefix")
    
    # GraphQL 요청 감지
    try:
        if request.headers.get("Content-Type") == "application/json":
            body = await request.body()
            body_json = json.loads(body) if body else {}

            if isinstance(body_json, dict) and "query" in body_json:
                is_graphql = True
                logger.info("Detected GraphQL request")

    except json.JSONDecodeError:
        pass  # JSON이 아니면 일반 REST 요청으로 처리

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method="POST" if is_graphql else request.method,  # GraphQL 요청이면 POST 고정
                url=url,
                headers=dict(request.headers),
                cookies=request.cookies,
                data=await request.body() if not is_graphql else json.dumps(body_json),
            )
            logger.debug(f"Forwarded request to {url} with status {response.status_code}")

            return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get('Content-Type'))
    except Exception as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        raise HTTPException(status_code=500, detail="Error forwarding request to proxy server")
