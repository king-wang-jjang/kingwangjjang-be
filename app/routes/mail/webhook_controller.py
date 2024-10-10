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
class WebhookMail(BaseModel):
    FromName: str
    MessageStream: str
    From: str
    FromFull: dict
    To: str
    ToFull: list
    Cc: str
    CcFull: list
    Bcc: str
    BccFull: list
    OriginalRecipient: str
    Subject: str
    MessageID: str
    ReplyTo: str
    MailboxHash: str
    Date: str
    TextBody: str
    HtmlBody: str
    StrippedTextReply: str
    RawEmail: str
    Tag: str
    Headers: list
    Attachments: list


@router.post("/webhook/mail/inbound")
def webhook_mail(request: WebhookMail):
    logger.info("Webhook received for inbound mail")

    try:
        # Save email data to MongoDB
        db_id = db_controller.insert_one('mail', request.dict()).inserted_id
        logger.info(f"Email data inserted into MongoDB with ID: {db_id}")

        # Create Slack payload and send notification
        mail_webhook = MailWebhooks()
        payload = mail_webhook.create_payload(request, db_id)
        mail_webhook.send_slack(payload)
        logger.info(f"Slack notification sent successfully for email ID: {db_id}")

    except Exception as e:
        logger.error(f"Error processing webhook mail: {e}")
        raise HTTPException(status_code=500, detail="Error processing the inbound mail webhook")
