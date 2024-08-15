import logging
from logging import handlers
import os
import sys
import requests
from app.config import Config
from colorama import Fore, Style, init
from app.db.mongo_controller import MongoController
init(autoreset=True)  # colorama 초기화

class SlackWebhookHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.webhook_url = Config().get_env("WEBHOOK_URL")

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            payload = self.create_payload(record)
            self.send_to_slack(payload)
        else:
            self.print_colored_log(log_entry, record.levelname)

    def create_payload(self, record):
        color_map = {
            "DEBUG": "#808080",   # Gray
            "INFO": "#00FF00",    # Green
            "WARNING": "#FFFF00", # Yellow
            "ERROR": "#FF0000",   # Red
            "CRITICAL": "#8B0000" # Dark Red
        }
        try:
            payload = {
                "attachments": [
                    {
                        "color": color_map.get(record.levelname),
                        "title": f"{record.levelname}!",
                        "fields": [
                            {
                                "title": "MESSAGE",
                                "value": record.message,
                                "short": False
                            },
                            {
                                "title": "TYPE",
                                "value": str(record.exc_info[0]),
                                "short": True
                            },
                            {
                                "title": "VALUE",
                                "value": str(record.exc_info[1]),
                                "short": True
                            },
                            {
                                "title": "TRACEBACK",
                                "value": str(record.exc_info[2]),
                                "short": True
                            },
                            {
                                "title": "FILE",
                                "value": record.filename,
                                "short": True
                            },
                            {
                                "title": "ERROR LINE",
                                "value": record.lineno,
                                "short": True
                            }
                        ],
                        "footer": str(record.__dict__)
                    }
                ]
            }
        except Exception as e:
            payload = {
                "attachments": [
                    {
                        "color": color_map.get(record.levelname),
                        "title": f"{record.levelname}! @everyone",
                        "fields": [
                            {
                                "title": "MESSAGE",
                                "value": record.message,
                                "short": False
                            },
                            {
                                "title": "FILE",
                                "value": record.filename,
                                "short": True
                            },
                            {
                                "title": "ERROR LINE",
                                "value": record.lineno,
                                "short": True
                            }
                        ],
                        "footer": str(record.__dict__)
                    }
                ]
            }
        return payload

    def send_to_slack(self, payload):
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending log to Slack: {e}")

    def print_colored_log(self, message, level):
        color_map = {
            "DEBUG": Fore.LIGHTBLACK_EX,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT
        }
        color = color_map.get(level, Fore.WHITE)  # Default to white if level not found
        print(f"{color}{message}")
class DBLOGHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.db_controller = MongoController()

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.db_controller.insert_one("log",dict(record.__dict__))
        else:
            self.print_colored_log(log_entry, record.levelname)


    def print_colored_log(self, message, level):
        color_map = {
            "DEBUG": Fore.LIGHTBLACK_EX,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT
        }
        color = color_map.get(level, Fore.WHITE)  # Default to white if level not found
        print(f"{color}{message}")
def setup_logger():
    logger = logging.getLogger("slack_logger")
    logger.setLevel(logging.DEBUG)  # DEBUG 레벨까지 모든 로그를 처리

    # 슬랙 웹훅 핸들러 추가
    slack_handler = SlackWebhookHandler()
    slack_handler.setLevel(logging.ERROR)  # ERROR 레벨까지 모든 로그를 처리
    # DB 웹훅 핸들러 추가
    db_handler = DBLOGHandler()
    db_handler.setLevel(logging.DEBUG)  # DEBUG 레벨까지 모든 로그를 처리
    # 로그 메시지 형식 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    slack_handler.setFormatter(formatter)

    # 핸들러를 로거에 추가
    logger.addHandler(slack_handler)
    logger.addHandler(db_handler)
    if Config.get_env("SERVER_RUN_MODE") == "TRUE":
        return logger
    else:
        log = logging.getLogger("")
        log.setLevel(logging.DEBUG)
        return log

def catch_exception(exc_type, exc_value, exc_traceback):
    # 로깅 모듈을 이용해 로거를 미리 등록해놔야 합니다.
    if Config.get_env("SERVER_RUN_MODE") == "TRUE":
        logger = logging.getLogger("slack_logger")
        logger.addHandler(DBLOGHandler())
    else:
        logger = logging.getLogger("")
    logger.error("Unexpected exception.", exc_info=(exc_type, exc_value, exc_traceback))
