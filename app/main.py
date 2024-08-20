from app.celery.schema import schema, task_status_schema
from strawberry.fastapi import GraphQLRouter
from app.middlewares import static_middleware
from app.routes.path import ApiPaths
from app.routes import index
from app.config import Config
import logging
from middlewares import cors_middleware
import uvicorn
from app.utils.loghandler import catch_exception
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.loghandler import setup_logger
from app.routes.user import user_controller
from app.routes.page import page_controller
from utils import lifespan
import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append("/app")
# from routes.auth import auth_controller
# from routes.board import board_controller
sys.excepthook = catch_exception


class IPFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/proxy"):
            if request.client.host != "127.0.0.1":
                raise HTTPException(status_code=403, detail="Access forbidden")
            response = await call_next(request)
        else:
            response = await call_next(request)
        return response


app = FastAPI(lifespan=lifespan.lifespan)
app.add_middleware(IPFilterMiddleware)
logger = setup_logger()
if Config.get_env("SERVER_RUN_MODE") == "TRUE":
    logging.getLogger("uvicorn.access").handlers = [logger.handlers[1]]
    logging.getLogger("uvicorn.error").handlers = [logger.handlers[1]]
cors_middleware.add(app)
# static_middleware.add(app)
# app.include_router(auth_controller.router)
app.include_router(page_controller.router, prefix=ApiPaths.PROXY)
app.include_router(user_controller.router, prefix=ApiPaths.PROXY)
# app.include_router(board_controller.router)

# ---------------------------------------------------
# -- LLM 할 때 사용될 예정 --
graphql_app = GraphQLRouter(schema)
task_status_app = GraphQLRouter(task_status_schema)

app.include_router(graphql_app, prefix=ApiPaths.GRAPHQL_WITH_PROXY)
app.include_router(task_status_app, prefix=ApiPaths.STATUS_WITH_PROXY)
app.include_router(index.router)

# ---------------------------------------------------

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True)
