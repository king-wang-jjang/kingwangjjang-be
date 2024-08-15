from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging
from celery.app.log import TaskFormatter
from celery.signals import after_setup_logger
from app.utils.loghandler import setup_logger
import logging
import celery.signals

celery_app = Celery(
    "worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.celery.tasks"],
)

celery_app.conf.update(
    task_routes={
        "app.celery.tasks.task_realtime_to_db": {"queue": "crawling_queue"},
    },
    result_expires=3600,
    beat_schedule={
        'realtime-to-db-every-5-minutes': {
            'task': 'app.celery.tasks.task_realtime_to_db',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
    },
)
celery_app.conf.update(
    worker_hijack_root_logger=False,  # Celery가 기본 로거를 사용하지 않도록 설정
)
@after_setup_logger.connect
def setup_task_logger(logger : logging.Logger, *args, **kwargs):
    logger.addHandler(setup_logger())
    # for handler in logger.handlers:
    #     handler.setFormatter(TaskFormatter('%(asctime)s - %(task_id)s - %(task_name)s - %(name)s - %(levelname)s - %(message)s'))

@celery.signals.setup_logging.connect
def on_celery_setup_logging(logger : logging.Logger, **kwargs):
    logger.addHandler(setup_logger())



if __name__ == "__main__":
    celery_app.start()