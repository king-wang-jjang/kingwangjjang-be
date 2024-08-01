from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from utils.oauth import oauth
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from services.web_crwaling.pagination import get_pagination_real_time_best,get_pagination_daily_best
from services.web_crwaling.views import board_summary,tag
from utils.loghandler import setup_logger
from utils.loghandler import catch_exception
from db.mongo_controller import MongoController
from typing import List, Optional
import string
import random
import sys
sys.excepthook = catch_exception
db_controller = MongoController()

def add_user(email : str, name : str):
    string_pool = string.ascii_lowercase  # 소문자
    result = ""  # 결과 값
    for i in range(30):
        result += random.choice(string_pool)  # 랜덤한 문자열 하나 선택

    return db_controller.insert_one('user',{'email':email,'name':name,'nick':result, 'role':"user"}).inserted_id
def get_user_by_email(email : str):
    try:
        return db_controller.find('user',{'email':email})[0]
    except:
        return None
