import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings, MongoClient

from db.mongo_controller import MongoController
from services.web_crwaling.community_website.instiz import Instiz
from services.web_crwaling.community_website.ppomppu import Ppomppu
from services.web_crwaling.community_website.ruliweb import Ruliweb
from services.web_crwaling.community_website.theqoo import Theqoo
from services.web_crwaling.community_website.ygosu import Ygosu
from services.web_crwaling.community_website.dcinside import Dcinside

from utils.llm import LLM
from constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE, SITE_YGOSU,SITE_PPOMPPU,SITE_THEQOO,SITE_INSTIZ,SITE_RULIWEB
from utils.loghandler import setup_logger
from utils.loghandler import catch_exception
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
            "timestamp": datetime.datetime.now()
        }
        collection = db_controller.find('Comment',{"board_id": board_id, "site": site})
        db_controller.insert_one('Comment',comment_data)
        return collection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

