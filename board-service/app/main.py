import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
import logging
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.config import Config

from app.utils import lifespan
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger
from app.graphql.modules.sample.sample_schema import schema as samele
from app.graphql.modules.board.board_schema import schema 

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
app.include_router(graphql_app, prefix="/board-graphql")

if __name__ == "__main__":
    logger.info("Starting uvicorn server")
    uvicorn.run("main:app", host="0.0.0.0", port=33333, reload=True)
