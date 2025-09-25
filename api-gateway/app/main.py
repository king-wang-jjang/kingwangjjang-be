# from typing import Union
import sys
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.routes import index
from app.routes.auth import auth_controllers
from app.middlewares.auth_middleware import AuthMiddleware, UserInfoMiddleware
from fastapi import FastAPI

app = FastAPI()
origins = [
    "http://localhost:8083",  
    "https://xn--hz2b47s.kr",
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

app.include_router(auth_controllers.router)
app.include_router(index.router)

