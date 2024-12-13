# app/tasks.py

from ..celery_app import celery_app
from app.utils.loghandler import DBLOGHandler,SlackWebhookHandler

@celery_app.task
def task_send_to_slack(payload):
    return SlackWebhookHandler().send_to_slack(payload)
@celery_app.task
def task_record_db(record):
    return DBLOGHandler().record_db(record)