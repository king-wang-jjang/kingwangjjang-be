import httpx
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from app.utils.oauth import oauth

router = APIRouter()


async def get_oauth_token(request: Request) -> str:
    """Retrieve the OAuth token from the request."""
    user_id = request.headers.get('Bearer')  # Example of how you might get user ID
    oauth.google.introspect_token()
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in request headers")

    token = oauth.get_token(user_id=user_id, provider_name='google')
    if not token:
        raise HTTPException(status_code=401, detail="OAuth token not found")
    return token


async def forward_request(request: Request, base_url: str, path: str, token: str):
    url = f"{base_url}/{path}"
    headers = dict(request.headers)
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
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
)
async def proxy(request: Request, path: str, token: str = Depends(get_oauth_token)):
    base_url = "http://localhost:8000/proxy"

    response = await forward_request(request, base_url, path, token)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )
