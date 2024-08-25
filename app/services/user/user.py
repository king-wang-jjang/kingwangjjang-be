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

# from services.web_crwaling.pagination import get_pagination_real_time_best,get_pagination_daily_best
# from services.web_crwaling.views import board_summary,tag
from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception
from app.db.mongo_controller import MongoController
from typing import List, Optional
from faker import Faker
from faker.providers import address, company, date_time, phone_number, person
import string
import random
import sys

sys.excepthook = catch_exception
db_controller = MongoController()
fake = Faker("ko_KR")


def add_user(email: str, name: str):
    return db_controller.insert_one(
        "user", {"email": email, "name": name, "nick": fake.user_name(), "role": "user"}
    ).inserted_id


def get_user_by_email(email: str):
    try:
        return db_controller.find("user", {"email": email})[0]
    except:
        return None


def get_user_by_id(id: str):
    try:
        return db_controller.find("user", {"_id": id})[0]
    except:
        return None
