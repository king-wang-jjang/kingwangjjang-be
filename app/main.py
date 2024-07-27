import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from utils import lifespan
from routes.auth import auth_controller
from routes.page import page_controller
from routes.user import user_controller
from routes.board import board_controller
from utils.loghandler import setup_logger
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception

import uvicorn
from middlewares import cors_middleware
import logging

# from middlewares import static_middleware

app = FastAPI(lifespan=lifespan)
logger = setup_logger()
logging.getLogger("uvicorn.access").handlers = [logger.handlers[0]]
logging.getLogger("uvicorn.error").handlers = [logger.handlers[0]]
cors_middleware.add(app)
# static_middleware.add(app)

# app.include_router(auth_controller.router)
app.include_router(page_controller.router)
app.include_router(user_controller.router)
app.include_router(board_controller.router)

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=3000,reload=True)