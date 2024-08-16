import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings, MongoClient

from app.db.mongo_controller import MongoController

from app.utils.loghandler import catch_exception
import sys
import datetime
sys.excepthook = catch_exception
db_controller = MongoController()


def board_comment_get(board_id, site):
    try:
        collection = db_controller.find('Comment',{"board_id": board_id, "site": site})
        print(collection)
        return collection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
