from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

from tasks import real_time_scheduler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

app.config_from_object('django.conf:settings', namespace='task')

app.autodiscover_tasks()


from kingwangjjang.kingwangjjang.config.celery import app

# app = Celery('tasks', backend='redis://localhost:6379', broker='redis://localhost:6379')
 
@app.task()
def task_real_time(x, y):
    real_time_scheduler()

    return {'add': x + y}