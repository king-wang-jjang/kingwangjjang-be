import os
import sys

import LLM.schema

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from utils import lifespan
# from routes.auth import auth_controller
from app.routes.page import page_controller
from app.routes.user import user_controller
# from routes.board import board_controller
from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception

import uvicorn
from middlewares import cors_middleware
import logging
from app.config import Config
# from middlewares import static_middleware

app = FastAPI(lifespan=lifespan.lifespan)
logger = setup_logger()
if Config.get_env("SERVER_RUN_MODE") == "TRUE":
    logging.getLogger("uvicorn.access").handlers = [logger.handlers[0]]
    logging.getLogger("uvicorn.error").handlers = [logger.handlers[0]]
cors_middleware.add(app)
# static_middleware.add(app)

# app.include_router(auth_controller.router)
app.include_router(page_controller.router)
app.include_router(user_controller.router)
# app.include_router(board_controller.router)

# ---------------------------------------------------
# -- LLM 할 때 사용될 예정 --
from strawberry.fastapi import GraphQLRouter
from app.celery.schema import schema,task_status_schema
graphql_app = GraphQLRouter(schema)
task_status_app = GraphQLRouter(task_status_schema)

app.include_router(graphql_app, prefix="/graphql")
app.include_router(task_status_app, prefix="/status")
# ---------------------------------------------------

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000,reload=True)