import random
from datetime import timedelta
from enum import Enum
from utils.loghandler import catch_exception
sys.excepthook = catch_exception
DEFAULT_GPT_ANSWER = 'GPT 생성 중입니다. 이미지가 많은 경우 오래 걸립니다.'
SITE_DCINSIDE = 'dcinside'
SITE_YGOSU = 'ygosu'
SITE_PPOMPPU = 'ppomppu'
SITE_THEQOO = 'theqoo'
SITE_INSTIZ = 'instiz'
SITE_RULIWEB = 'ruliweb'
COOKIES_KEY_NAME = "session_token"
SESSION_TIME = timedelta(days=30)
HASH_SALT = random.Random().randint(1, 100)