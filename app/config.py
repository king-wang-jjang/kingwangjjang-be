import os
from dotenv import load_dotenv,find_dotenv
import logging
from utils.loghandler import setup_logger
logger = setup_logger()

class Config:
    def __init__(self):
        if find_dotenv() == "":
            logger.info("ENV로더 : env 파일이 감지되지 않음.")
            if os.getenv("DB_HOST") == None:
                logger.error("ENV가 설정되지 않음!!")
        else:
            load_dotenv(find_dotenv())

    @staticmethod
    def get_env(env: str):
        if os.getenv(env) == None:
            logger.error(f"ENV가 알수없는 애러로 불러오지 못함. {env}")
            return None
        else:
            return os.getenv(env)
