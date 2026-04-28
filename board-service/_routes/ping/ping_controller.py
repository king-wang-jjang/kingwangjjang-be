from fastapi import APIRouter, FastAPI
import logging

# FastAPI application
app = FastAPI()
router = APIRouter()

# Logger setup
logger = logging.getLogger(__name__)


# Pydantic model for webhook data
@router.head("/ping")
def webhook_mail():
    return {"code":"200","message": "Pong!"}
