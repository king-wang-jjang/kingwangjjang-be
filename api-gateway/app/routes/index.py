import logging
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
import sys

from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger
# Global exception handler and logger setup
sys.excepthook = catch_exception
logger = setup_logger()

router = APIRouter()


async def forward_request(request: Request, base_url: str, path: str, token: str = None) -> httpx.Response:
    """프록시 서버로 요청을 전달합니다."""
    url = f"{base_url}/{path}"
    headers = dict(request.headers)

    if token and not request.url.path.startswith("/callback") and not request.url.path.startswith("/login"):
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                cookies=request.cookies,
                data=await request.body(),
            )
            logger.debug(f"Forwarded request to {url} with status {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        raise HTTPException(status_code=500, detail="Error forwarding request to proxy server")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    base_url = "http://localhost:8002/"+ path
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=base_url,
                headers=dict(response.headers),
                cookies=request.cookies,
                data=await request.body(),
            )
            logger.debug(f"Forwarded request to {base_url} with status {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error forwarding request to {base_url}: {e}")
        raise HTTPException(status_code=500, detail="Error forwarding request to proxy server")
