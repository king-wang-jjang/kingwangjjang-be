import logging
import sys

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app.utils.loghandler import catch_exception, setup_logger
from app.utils.oauth import JWT, oauth

sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()


async def forward_request(
    request: Request, base_url: str, path: str, token: str = None
) -> httpx.Response:
    """프록시 서버로 요청을 전달합니다."""
    url = f"{base_url}/{path}"
    headers = dict(request.headers)
    if not request.url.path.startswith("/callback") and not request.url.path.startswith(
        "/login"
    ):
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            cookies=request.cookies,
            data=await request.body(),
        )

    return response


@router.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
)
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    base_url = "http://localhost:8000/proxy"
    token = None
    if not request.url.path.startswith("/callback") and not request.url.path.startswith(
        "/login"
    ):
        try:
            token = request.headers.get("Authorization").split("Bearer ")[1]
        except HTTPException as e:
            logger.debug("Can't find token on your Requests")
            raise HTTPException(
                status_code=401, detail="Can't find token on your Requests"
            )
        # ID 토큰 검증
        try:
            token_data = JWT().decode(token)
            logger.debug(f"JWT token issued: {token_data}")
        except HTTPException as e:
            logger.debug("Failed to verify your JWT token.")
            raise HTTPException(
                status_code=401, detail="Failed to verify your JWT token."
            )

    # 요청을 프록시 서버로 전달
    response = await forward_request(request, base_url, path, token)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
