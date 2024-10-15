import logging
import sys

import httpx
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response

from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger
from app.utils.oauth import JWT
from app.utils.oauth import oauth

# Global exception handler and logger setup
sys.excepthook = catch_exception
logger = setup_logger()

router = APIRouter()


async def forward_request(request: Request,
                          base_url: str,
                          path: str,
                          token: str = None) -> httpx.Response:
    """프록시 서버로 요청을 전달합니다."""
    url = f"{base_url}/{path}"
    headers = dict(request.headers)

    if (token and not request.url.path.startswith("/callback")
            and not request.url.path.startswith("/login")):
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
            logger.debug(
                f"Forwarded request to {url} with status {response.status_code}"
            )
        return response
    except Exception as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        raise HTTPException(status_code=500,
                            detail="Error forwarding request to proxy server")


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    base_url = "http://localhost:8000/proxy"
    token = None

    # Token handling except for callback and login routes
    if (not request.url.path.startswith("/callback")
            and not request.url.path.startswith("/login")
            and not request.url.path.startswith("/ping")
            and not request.url.path.startswith("/webhook")):
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                logger.debug("Authorization header missing")
                raise HTTPException(status_code=401,
                                    detail="Authorization header is missing")

            token = auth_header.split("Bearer ")[1]
            logger.debug(f"Extracted token: {token}")

        except IndexError:
            logger.debug("Malformed Authorization header")
            raise HTTPException(status_code=401,
                                detail="Malformed Authorization header")

        # ID 토큰 검증
        try:
            token_data = JWT().decode(token)
            logger.debug(f"JWT token verified successfully: {token_data}")
        except Exception as e:
            logger.debug(f"JWT token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid JWT token")

    # Forward the request to the proxy server
    response = await forward_request(request, base_url, path, token)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
