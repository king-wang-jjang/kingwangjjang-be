from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from app.services.webhook.mail import MailWebhooks
from app.db.mongo_controller import MongoController
import logging

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
    return {"code":"200","message": "Pong!"}