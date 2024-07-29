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
db_controller = MongoController()

def get_likes(board_id: str, site: str):
    try:
        count_object = db_controller.find('Count', {'board_id': board_id, 'site': site})[0]
        return count_object['likes']

    except IndexError:
        count_object = db_controller.insert_one('Count',{'board_id': board_id, 'site': site, 'likes': 0, 'views': 0})
        return 0


def add_likes(board_id: str, site: str):
    try:
        count_object = db_controller.find('Count', {'board_id': board_id, 'site': site})[0]
        db_controller.update_one('Count',
                                 {'_id': count_object['_id']},
                                 {'$set': {'likes': count_object['likes'] + 1}})
        return count_object['likes'] + 1
    except IndexError:
        count_object = db_controller.insert_one('Count', {'board_id': board_id, 'site': site, 'likes': 0, 'views': 0})
        db_controller.update_one('Count',
                                 {'_id': count_object['_id']},
                                 {'$set': {'likes': count_object['likes'] + 1}})
        return 1