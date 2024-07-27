from celery import Celery
from config import Config
celery_app = Celery(
                __name__,
                broker=Config().get_env('CELERY_BROKER_URL'),
                backend=Config().get_env('CELERY_BACKEND_URL')
            )
celery_app.config_from_object('celeryconfig')