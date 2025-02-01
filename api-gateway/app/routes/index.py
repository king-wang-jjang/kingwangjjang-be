import logging
from fastapi.responses import RedirectResponse
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
import sys

from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

sys.excepthook = catch_exception
logger = setup_logger()
router = APIRouter()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    url = ""
    
    # 경로를 기반으로 서비스 포트 설정
    if path.startswith("boardservice/"):
        port = 33333
        path = path[len("boardservice/"):]  # 'boardservice/' 부분 제거
        url = f"http://localhost:{port}/{path}" 
    elif path.startswith("schedulerapp/"):
        port = 8003
        path = path[len("schedulerapp/"):]
        url = f"http://localhost:{port}/{path}"
    elif path.startswith("auth/"):
        port = 33334
        path = path[len("auth/"):]
        url = f"http://localhost:{port}/{path}"
    else:
        raise HTTPException(status_code=404, detail="Invalid path prefix")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                cookies=request.cookies,
                data=await request.body(),
            )

            # 리다이렉트 응답일 경우 직접 Location 헤더를 설정
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
