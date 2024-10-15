import logging

from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from pydantic import BaseModel

from app.db.mongo_controller import MongoController
from app.services.webhook.mail import MailWebhooks

# MongoDB controller
db_controller = MongoController()

# FastAPI application
app = FastAPI()
router = APIRouter()

# Logger setup
logger = logging.getLogger(__name__)


# Pydantic model for webhook data
@router.head("/ping")
def webhook_mail():
    """ """
    return {"code": "200", "message": "Pong!"}
