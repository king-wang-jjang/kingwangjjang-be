# celeryconfig.py

from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Seoul'
enable_utc = True


