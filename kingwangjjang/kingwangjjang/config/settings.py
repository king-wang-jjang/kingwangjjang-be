
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_ACCEPT_CONTENT = ['json','application/text', 'application/json']

from celery.schedules import crontab
WSGI_APPLICATION = 'config.wsgi.application'
CELERY_BEAT_SCHEDULE = {
    'run-every-5-minutes-30-seconds': {
        'task': 'tasks.task_real_time',
        'schedule': crontab(minute='*/5.5'),
    },
}