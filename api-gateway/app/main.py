import os
import sys
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.routes import index
from app.config import Config
from app.middlewares.auth_middleware import AuthMiddleware, UserInfoMiddleware, TokenRefreshMiddleware
from fastapi import FastAPI

app = FastAPI()
CORS_ORIGINS = [
    "http://localhost:8083",  
    "http://localhost:8084",
    "http://127.0.0.1:8083",
    "http://127.0.0.1:8084",
    "https://xn--hz2b47s.kr",
]
origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(CORS_ORIGINS)).split(",")
    if origin.strip()
]

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 인증 미들웨어 (CORS 이후, 라우터 이전에 등록)
app.add_middleware(AuthMiddleware)

# 사용자 정보 헤더 추가 미들웨어
app.add_middleware(UserInfoMiddleware)

# 토큰 자동 갱신 미들웨어 (응답 처리)
app.add_middleware(TokenRefreshMiddleware)

def _crawler_media_root() -> Path:
    Config()
    media_root = os.getenv("CRAWLER_MEDIA_ROOT") or "CrawlScheduler/media"
    path = Path(media_root).expanduser()
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[3] / path


media_root = _crawler_media_root()
if media_root.exists():
    app.mount("/static/media", StaticFiles(directory=str(media_root)), name="crawler-media")

app.include_router(index.router)
