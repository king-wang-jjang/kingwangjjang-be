from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from utils.oauth import oauth
from fastapi import APIRouter, FastAPI, HTTPException, Request
from services.user.user import get_user_by_email,add_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, time, timedelta
import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
from services.web_crwaling.pagination import get_pagination_real_time_best,get_pagination_daily_best
from services.web_crwaling.views import board_summary,tag
from typing import List, Optional
from config import Config
import sys
from services.webhook.mail import Mail_webhooks
from db.mongo_controller import MongoController
db_controller = MongoController()

app = FastAPI()
router = APIRouter()
class Webhook_mail(BaseModel):
    FromName : str
    MessageStream : str
    From : str
    FromFull : dict
    To : str
    ToFull : list
    Cc : str
    CcFull : list
    Bcc : str
    BccFull : list
    OriginalRecipient : str
    Subject : str
    MessageID : str
    ReplyTo : str
    MailboxHash : str
    Date : str
    TextBody : str
    HtmlBody : str
    StrippedTextReply : str
    RawEmail : str
    Tag : str
    Headers : list
    Attachments : list

@router.post("/webhook/mail/inbound")
def webhook_mail(request: Webhook_mail):
    db_id = db_controller.insert_one('mail',request.__dict__).inserted_id
    payload = Mail_webhooks().create_payload(request,db_id)
    Mail_webhooks().send_slack(payload)



