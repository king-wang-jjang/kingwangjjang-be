from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from app.utils.oauth import oauth
from fastapi import APIRouter, FastAPI, HTTPException, Request
from app.services.user.user import get_user_by_email, add_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional
from app.config import Config
from app.utils.oauth import oauth, JWT
import sys
# from .google_service import auth_via_google,login_via_google
# from .kakao_service import auth_via_google,login_via_google
from datetime import datetime, timedelta

app = FastAPI()
router = APIRouter()


@router.get("/login/google")
async def login_via_google(request: Request):
    if Config().get_env("SERVER_RUN_MODE") == "TRUE":
        redirect_uri = "https://api.top1.kr/callback/google"
    else:
        redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google")
async def auth_via_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token['userinfo']

    if not get_user_by_email(user["email"]) == None:
        data = get_user_by_email(user["email"])
        data["_id"] = str(data["_id"])
        data["exp"] = datetime.utcnow() + timedelta(days=3)
        data["jwt"] = JWT().encode(data)
        return data
    else:
        add_user(user["email"], user["name"])
        data = get_user_by_email(user["email"])
        data["_id"] = str(data["_id"])
        data["jwt"] = JWT().encode(data)
        return data
    # return dict(user)
