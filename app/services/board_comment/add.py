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


def board_comment_add(board_id, site,userid,comment):
    try:
        comment_data = {
            "board_id": board_id,
            "site": site,
            "user_id": userid,
            "comment": comment,
            "reply" : list(),
            "timestamp": datetime.datetime.now()
        }
        collection = db_controller.find('Comment',{"board_id": board_id, "site": site})
        db_controller.insert_one('Comment',comment_data)
        return collection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def board_reply_add(board_id, site,userid,reply, parrent_comment):
    try:
        comment_data = {
            "board_id": board_id,
            "site": site,
            "user_id": userid,
            "comment": reply,
            "timestamp": datetime.datetime.now()
        }
        replys = db_controller.find('Comment', {"_id":parrent_comment})["reply"]
        replys.append(comment_data)
        db_controller.update_one("Comment", {"_id":parrent_comment}, {"$set":replys})
        return db_controller.find('Comment', {"_id":parrent_comment})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

