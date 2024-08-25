import logging
import random
import string
import sys
from datetime import datetime
from typing import List, Optional

import strawberry
from faker import Faker
from faker.providers import address, company, date_time, person, phone_number
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from strawberry.fastapi import GraphQLRouter
from utils.oauth import oauth

from app.db.mongo_controller import MongoController
# from services.web_crwaling.pagination import get_pagination_real_time_best,get_pagination_daily_best
# from services.web_crwaling.views import board_summary,tag
from app.utils.loghandler import catch_exception, setup_logger

sys.excepthook = catch_exception
db_controller = MongoController()
fake = Faker("ko_KR")


def add_user(email: str, name: str):
    """

    :param email: str: 
    :param name: str: 

    """
    return db_controller.insert_one(
        "user", {"email": email, "name": name, "nick": fake.user_name(), "role": "user"}
    ).inserted_id


def get_user_by_email(email: str):
    """

    :param email: str: 

    """
    try:
        return db_controller.find("user", {"email": email})[0]
    except:
        return None


def get_user_by_id(id: str):
    """

    :param id: str: 

    """
    try:
        return db_controller.find("user", {"_id": id})[0]
    except:
        return None
