import httpx
from fastapi import APIRouter, Request, Response

from app.constants import COOKIES_KEY_NAME
from app.utils.oauth import oauth

router = APIRouter()


class Router:
    """ """

    def __init__(self):
        pass


async def forward_request(request: Request, base_url: str, path: str, oauth):
    url = f"{base_url}/{path}"
    headers = dict(request.headers)
    headers["oauth"] = oauth
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
async def proxy(request: Request, path: str):
    base_url = "http://localhost:8000/proxy"
    response = await forward_request(
        request, base_url, path, oauth.google.authorize_access_token(request)
    )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
