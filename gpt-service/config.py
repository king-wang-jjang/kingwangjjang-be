import os
from dotenv import load_dotenv,find_dotenv
import logging
# from utils.loghandler import setup_logger
# *** 해당 코드에 로깅코드 작성시 애러발생 ***
logger = logging.getLogger("")

class Config:
    def __init__(self):
        if find_dotenv() == "":
            logger.info("ENV로더 : env 파일이 감지되지 않음.")
            logger.info("ENV 기본 파일 없이 프로세스 환경 변수를 사용합니다.")
        else:
            load_dotenv(find_dotenv())

    @staticmethod
    def get_env(env: str):
        if os.getenv(env) == None:
            logger.error(f"ENV가 알 수 없는 애러로 불러오지 못함. {env}")
            return None
        else:
            return os.getenv(env)
