import logging
import requests
from colorama import Fore, init, Style
from app.config import Config
from app.db.mongo_controller import MongoController
import threading
import bson
import uuid
from logging.handlers import TimedRotatingFileHandler
import os 
init(autoreset=True)  # colorama 초기화

class BaseWebhookHandler(logging.Handler):
    """ 기본 웹훅 핸들러 클래스 """
    
    def __init__(self, webhook_url_env):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.webhook_url = Config().get_env(webhook_url_env)

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            payload = self.create_payload(record)
            threading.Thread(target=self.send_to_webhook, args=(payload,)).start()
        else:
            self.print_colored_log(log_entry, record.levelname)

    def print_colored_log(self, message, level):
        color_map = {
            "DEBUG": Fore.LIGHTBLACK_EX,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }
        color = color_map.get(level, Fore.WHITE)
        print(f"{color}{message}")

    def create_payload(self, record):
        raise NotImplementedError("Subclasses should implement this method.")

    def send_to_webhook(self, payload):
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending log to webhook: {e}")

class DiscordWebhookHandler(BaseWebhookHandler):
    """ Discord에 로그를 전송하는 핸들러 """

    def __init__(self):
        super().__init__("DISCORD_WEBHOOK_URL")

    def create_payload(self, record):
        color_map = {
            "DEBUG": 8421504,  # Gray
            "INFO": 65280,     # Green
            "WARNING": 16776960, # Yellow
            "ERROR": 16711680,  # Red
            "CRITICAL": 9109504  # Dark Red
        }
        return self._create_payload(record, color_map)

    def _create_payload(self, record, color_map):
        try:
            payload = {
                "embeds": [{
                    "title": f"{record.levelname}!",
                    "description": record.message,
                    "color": color_map.get(record.levelname),
                    "fields": self._get_fields(record)
                }]
            }
        except Exception:
            payload = {
                "embeds": [{
                    "title": f"{record.levelname}!",
                    "description": record.message,
                    "color": color_map.get(record.levelname),
                    "fields": self._get_basic_fields(record)
                }]
            }
        return payload

    def _get_fields(self, record):
        return [
            {"name": "FILE", "value": record.filename, "inline": True},
            {"name": "ERROR LINE", "value": str(record.lineno), "inline": True},
            {"name": "TYPE", "value": str(record.exc_info[0]), "inline": True} if record.exc_info else {},
            {"name": "VALUE", "value": str(record.exc_info[1]), "inline": True} if record.exc_info else {},
            {"name": "TRACEBACK", "value": str(record.exc_info[2]), "inline": False} if record.exc_info else {}
        ]

    def _get_basic_fields(self, record):
        return [
            {"name": "FILE", "value": record.filename, "inline": True},
            {"name": "ERROR LINE", "value": str(record.lineno), "inline": True}
        ]

class SlackWebhookHandler(BaseWebhookHandler):
    """ Slack에 로그를 전송하는 핸들러 """

    def __init__(self):
        super().__init__("WEBHOOK_URL")

    def create_payload(self, record):
        color_map = {
            "DEBUG": "#808080",  # Gray
            "INFO": "#00FF00",  # Green
            "WARNING": "#FFFF00",  # Yellow
            "ERROR": "#FF0000",  # Red
            "CRITICAL": "#8B0000"  # Dark Red
        }
        return self._create_payload(record, color_map)

    def _create_payload(self, record, color_map):
        try:
            payload = {
                "attachments": [{
                    "color": color_map.get(record.levelname),
                    "title": f"{record.levelname}!",
                    "fields": self._get_fields(record),
                    "footer": str(record.__dict__)
                }]
            }
        except Exception:
            payload = {
                "attachments": [{
                    "color": color_map.get(record.levelname),
                    "title": f"{record.levelname}! @everyone",
                    "fields": self._get_basic_fields(record),
                    "footer": str(record.__dict__)
                }]
            }
        return payload

    def _get_fields(self, record):
        return [
            {"title": "MESSAGE", "value": record.message, "short": False},
            {"title": "TYPE", "value": str(record.exc_info[0]), "short": True},
            {"title": "VALUE", "value": str(record.exc_info[1]), "short": True},
            {"title": "TRACEBACK", "value": str(record.exc_info[2]), "short": True},
            {"title": "FILE", "value": record.filename, "short": True},
            {"title": "ERROR LINE", "value": record.lineno, "short": True}
        ]

    def _get_basic_fields(self, record):
        return [
            {"title": "MESSAGE", "value": record.message, "short": False},
            {"title": "FILE", "value": record.filename, "short": True},
            {"title": "ERROR LINE", "value": record.lineno, "short": True}
        ]

class DBLOGHandler(logging.Handler):
    """ MongoDB에 로그를 저장하는 핸들러 """

    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.db_controller = MongoController()

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.record_db(record)
        else:
            self.print_colored_log(log_entry, record.levelname)

    def print_colored_log(self, message, level):
        color_map = {
            "DEBUG": Fore.LIGHTBLACK_EX,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }
        color = color_map.get(level, Fore.WHITE)
        print(f"{color}{message}")

    def record_db(self, record):
        data = dict(record.__dict__)
        data["server"] = Config().get_env("SERVER_TYPE")

        # Add unique ID or timestamp to prevent duplicate handling
        if "unique_id" not in data:
            data["unique_id"] = str(uuid.uuid4())

        # Remove or convert non-serializable types to string
        for key, value in data.items():
            try:
                bson.BSON.encode({key: value})
            except Exception:
                data[key] = str(value)

        try:
            self.db_controller.insert_one("log", data)
            print("Log successfully recorded in DB.")
        except Exception as e:
            print(f"Error recording log to DB: {e}")

def crawler_logger():
    logger = logging.getLogger("crawler")
    logger.setLevel(logging.INFO)

    # 로그 폴더가 없으면 생성
    log_directory = "log"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # 날짜별로 로그 파일을 생성하기 위한 핸들러 설정
    file_handler = logging.handlers.TimedRotatingFileHandler(f"{log_directory}/crawler.log", when="midnight", interval=7, backupCount=30)
    file_handler.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARN)

    # 포맷 설정
    formatter = logging.Formatter("%(levelname)s: [%(asctime)s]%(name)s %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # 기본 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # # 추가 핸들러 등록
    # logger.addHandler(db_handler)
    # logger.addHandler(discord_handler)
    # logger.addHandler(slack_handler)

    # 상위 로거로 전파 방지
    logger.propagate = False

    return logger

def setup_logger():
    logger = logging.getLogger("top1.kr")
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
