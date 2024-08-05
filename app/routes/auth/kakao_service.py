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
sys.excepthook = catch_exception

app = FastAPI()
router = APIRouter()
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return None
    # return await oauth.kakao.authorize_redirect(request, "http://localhost:8000/auth/kakao")

async def auth_via_google(request: Request):
    token = await oauth.kakao.authorize_access_token(request)
    print(token)
    user = token['userinfo']
    print(user)
    if not get_user_by_email(user["email"]) == None:
        data =  get_user_by_email(user["email"])
        data["_id"] = str(data["_id"])
        return data
    else:
        add_user(user["email"],user["name"])
        data = get_user_by_email(user["email"])
        data["_id"] = str(data["_id"])
        return data
    # return dict(user)
