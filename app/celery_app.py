from celery import Celery
from config import Config
from utils.loghandler import catch_exception
import sys

sys.excepthook = catch_exception
celery_app = Celery(
                __name__,
                broker=Config().get_env('CELERY_BROKER_URL'),
                backend=Config().get_env('CELERY_BACKEND_URL')
            )
celery_app.config_from_object('celeryconfig')