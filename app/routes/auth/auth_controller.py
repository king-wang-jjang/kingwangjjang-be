from utils.loghandler import catch_exception
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from utils.oauth import oauth
from fastapi import APIRouter, FastAPI, HTTPException, Request
from services.user.user import get_user_by_email,add_user
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
from typing import List, Optional
import sys
from .google_service import auth_via_google,login_via_google
# from .kakao_service import auth_via_google,login_via_google

sys.excepthook = catch_exception

app = FastAPI()
router = APIRouter()

@router.get("/login/google")
async def login_via_google(request: Request):
    return await login_via_google(request)

@router.get("/callback/google")
async def auth_via_google(request: Request):
    return await auth_via_google(request)