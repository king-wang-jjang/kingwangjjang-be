import logging
import logging.handlers
from colorama import Fore, init, Style
from app.config import Config
import os 
init(autoreset=True)  # colorama 초기화

def setup_logger():
    logger = logging.getLogger("api-gateway")
    logger.setLevel(logging.INFO)

    # 로그 폴더가 없으면 생성
    log_directory = "log"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # 날짜별로 로그 파일을 생성하기 위한 핸들러 설정
    file_handler = logging.handlers.TimedRotatingFileHandler(f"{log_directory}/app.log", when="midnight", interval=7, backupCount=30)
    file_handler.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter("%(levelname)s: [%(asctime)s]%(name)s %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # 기본 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # # 추가 핸들러 설정
    # db_handler = DBLOGHandler()
    # db_handler.setLevel(logging.DEBUG)
    # db_handler.setFormatter(formatter)

    # discord_handler = DiscordWebhookHandler()
    # discord_handler.setLevel(logging.ERROR)
    # discord_handler.setFormatter(formatter)

    # slack_handler = SlackWebhookHandler()
    # slack_handler.setLevel(logging.ERROR)
    # slack_handler.setFormatter(formatter)

    # # 추가 핸들러 등록
    # logger.addHandler(db_handler)
    # logger.addHandler(discord_handler)
    # logger.addHandler(slack_handler)

    # 상위 로거로 전파 방지
    logger.propagate = False

    return logger

    if Config.get_env("SERVER_RUN_MODE") == "TRUE":
        return logger
    else:
        log = logging.getLogger()
        log.addHandler(logging.StreamHandler())
        log.setLevel(logging.DEBUG)
        return log

def catch_exception(exc_type, exc_value, exc_traceback):
    logger = setup_logger() if Config.get_env("SERVER_RUN_MODE") == "TRUE" else logging.getLogger("")
    logger.exception("Unexpected exception.", exc_info=(exc_type, exc_value, exc_traceback))

# SERVER_RUN_MODE 상태 확인을 위한 디버깅 코드
logger = setup_logger()
logger.info((f"SERVER_RUN_MODE: {Config().get_env('SERVER_RUN_MODE')}"))
logger.info((f"SERVER_TYPE: {Config().get_env('SERVER_TYPE')}"))
