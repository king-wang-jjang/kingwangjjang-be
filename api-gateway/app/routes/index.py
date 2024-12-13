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

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str) -> Response:
    """프록시 요청을 처리합니다."""
    
    # prefix에 따라 포트 설정
    if path.startswith("boardservice/"):
        port = 8002
        path = path[len("boardservice/"):]
    elif path.startswith("schedulerapp/"):
        port = 8003
        path = path[len("schedulerapp/"):]
    else:
        raise HTTPException(status_code=404, detail="Invalid path prefix")

    url = f"http://localhost:{port}/{path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                cookies=request.cookies,
                data=await request.body(),
            )
            logger.debug(f"Forwarded request to {url} with status {response.status_code}")

            # 응답 내용을 JSON으로 변환하여 반환
            return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get('Content-Type'))
    except Exception as e:
        logger.error(f"Error forwarding request to {url}: {e}")
        raise HTTPException(status_code=500, detail="Error forwarding request to proxy server")
