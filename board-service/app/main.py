import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
import logging
from fastapi import FastAPI

from app.config import Config

from app.utils import lifespan
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger
from app.routes.boards import router as boards_router

# from routes.board import board_controller
sys.excepthook = catch_exception

app = FastAPI(lifespan=lifespan.lifespan)
logger = setup_logger()
if Config.get_env("SERVER_RUN_MODE") == "TRUE":
    logging.getLogger("uvicorn.access").handlers = [logger.handlers[1]]
    logging.getLogger("uvicorn.error").handlers = [logger.handlers[1]]
# static_middleware.add(app)
app.include_router(boards_router)

if __name__ == "__main__":
    logger.info("Starting uvicorn server")
    uvicorn.run("main:app", host="0.0.0.0", port=33333, reload=True)
