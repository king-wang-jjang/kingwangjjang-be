import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from utils import lifespan
from routes.auth import auth_controller
from routes.page import page_controller
from routes.user import user_controller
from routes.board import board_controller
from routes.mail import webhook_controller
from utils.loghandler import setup_logger
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from middlewares import cors_middleware
import logging
from config import Config
# from middlewares import static_middleware
from routes.auth import auth_controller

app = FastAPI(lifespan=lifespan.lifespan)
# app.add_middleware(SessionMiddleware, secret_key="some-random-string")

logger = setup_logger()
if Config.get_env("SERVER_RUN_MODE") == "TRUE":
    logging.getLogger("uvicorn.access").handlers = [logger.handlers[0]]
    logging.getLogger("uvicorn.error").handlers = [logger.handlers[0]]
cors_middleware.add(app)
# static_middleware.add(app)

# app.include_router(auth_controller.router)
app.include_router(page_controller.router)
app.include_router(user_controller.router)
app.include_router(board_controller.router)
app.include_router(auth_controller.router)
app.include_router(webhook_controller.router)
if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000,reload=True)