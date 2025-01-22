import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append("/Users/jason/pycharm/kingwangjjang-bes") #내부 모듈이 임포트 되기전에 가장 먼저 임포트 되야함.

import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from strawberry.fastapi import GraphQLRouter

from app.config import Config

# from app.routes.page import page_controller
# from app.routes.path import ApiPaths
# from app.routes.ping import ping_controller
# from app.routes.mail import webhook_controller

from app.utils import lifespan
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger
from app.schemas.sample_schema import schema as samele
from app.schemas.board_schema import schema 

# from routes.board import board_controller
sys.excepthook = catch_exception

app = FastAPI(lifespan=lifespan.lifespan)
logger = setup_logger()
if Config.get_env("SERVER_RUN_MODE") == "TRUE":
    logging.getLogger("uvicorn.access").handlers = [logger.handlers[1]]
    logging.getLogger("uvicorn.error").handlers = [logger.handlers[1]]
# static_middleware.add(app)

graphql_app = GraphQLRouter(samele)
app.include_router(graphql_app, prefix="/sample")

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
# ---------------------------------------------------
# -- LLM 할 때 사용될 예정 --
# graphql_app = GraphQLRouter(schema)
# task_status_app = GraphQLRouter(task_status_schema)

# app.include_router(graphql_app, prefix=ApiPaths.GRAPHQL)
# app.include_router(task_status_app, prefix=ApiPaths.STATUS)

# ---------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting uvicorn server")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
