# from typing import Union
import sys
from pathlib import Path

import uvicorn
import strawberry
from app.graphql.schema import Query, schema
from app.routes.auth import auth_controllers

from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

from fastapi import FastAPI

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (보안상 필요 시 특정 도메인만 허용)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, OPTIONS 등)
    allow_headers=["*"],  # 모든 헤더 허용
)

sys.excepthook = catch_exception
logger = setup_logger()

graphql_app = GraphQLRouter(schema)
app.include_router(auth_controllers.router)
app.include_router(graphql_app, prefix="/graphql") 

if __name__ == "__main__":
    logger.info("Starting uvicorn server")
    uvicorn.run("main:app", host="0.0.0.0", port=33334, reload=True)