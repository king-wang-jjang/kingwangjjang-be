import threading
import logging
from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings, MongoClient
from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger, catch_exception
import sys
import datetime

# Global exception handler setup
sys.excepthook = catch_exception

# Logger setup
logger = setup_logger()

# MongoDB controller instance
db_controller = MongoController()

def board_comment_get(board_id: str, site: str):
    logger.info(f"Fetching comments for board_id: {board_id} from site: {site}")
    try:
        collection = db_controller.find('Comment', {"board_id": board_id, "site": site})
        logger.info(f"Comments fetched for board_id {board_id}: {collection}")
        return collection
    except Exception as e:
        logger.error(f"Error fetching comments for board_id {board_id} from site {site}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching comments.")
