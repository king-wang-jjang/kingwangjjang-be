from datetime import timedelta
from enum import Enum

DEFAULT_GPT_ANSWER = 'GPT 생성 중입니다. 이미지가 많은 경우 오래 걸립니다.'
SITE_DCINSIDE = 'dcinside'
SITE_YGOSU = 'ygosu'
SITE_PPOMPPU = 'ppomppu'
COOKIES_KEY_NAME = "session_token"
SESSION_TIME = timedelta(days=30)