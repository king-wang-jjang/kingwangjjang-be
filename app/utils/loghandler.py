import logging
import os
import sys
from logging import handlers
import requests
from colorama import Fore, init, Style
from app.config import Config
from app.db.mongo_controller import MongoController
import threading
import bson
init(autoreset=True)  # colorama 초기화

class DiscordWebhookHandler(logging.Handler):
    """ Discord에 로그를 전송하는 핸들러 """

    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.webhook_url = Config().get_env("DISCORD_WEBHOOK_URL")

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            payload = self.create_payload(record)
            threading.Thread(target=self.send_to_discord, args=(payload,)).start()
        else:
            self.print_colored_log(log_entry, record.levelname)

    def create_payload(self, record):
        color_map = {
            "DEBUG": 8421504,  # Gray
            "INFO": 65280,     # Green
            "WARNING": 16776960, # Yellow
            "ERROR": 16711680,  # Red
            "CRITICAL": 9109504  # Dark Red
        }
        try:
            payload = {
                "embeds": [{
                    "title": f"{record.levelname}!",
                    "description": record.message,
                    "color": color_map.get(record.levelname),
                    "fields": [
                        {"name": "FILE", "value": record.filename, "inline": True},
                        {"name": "ERROR LINE", "value": str(record.lineno), "inline": True},
                        {"name": "TYPE", "value": str(record.exc_info[0]), "inline": True} if record.exc_info else {},
                        {"name": "VALUE", "value": str(record.exc_info[1]), "inline": True} if record.exc_info else {},
                        {"name": "TRACEBACK", "value": str(record.exc_info[2]), "inline": False} if record.exc_info else {}
                    ]
                }]
            }
        except Exception:
            payload = {
                "embeds": [{
                    "title": f"{record.levelname}!",
                    "description": record.message,
                    "color": color_map.get(record.levelname),
                    "fields": [
                        {"name": "FILE", "value": record.filename, "inline": True},
                        {"name": "ERROR LINE", "value": str(record.lineno), "inline": True}
                    ]
                }]
            }
        return payload

    def send_to_discord(self, payload):
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending log to Discord: {e}")

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

class SlackWebhookHandler(logging.Handler):
    """ Slack에 로그를 전송하는 핸들러 """

    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.webhook_url = Config().get_env("WEBHOOK_URL")

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            payload = self.create_payload(record)
            threading.Thread(target=self.send_to_slack, args=(payload,)).start()
        else:
            self.print_colored_log(log_entry, record.levelname)

    def create_payload(self, record):
        color_map = {
            "DEBUG": "#808080",  # Gray
            "INFO": "#00FF00",  # Green
            "WARNING": "#FFFF00",  # Yellow
            "ERROR": "#FF0000",  # Red
            "CRITICAL": "#8B0000"  # Dark Red
        }
        try:
            payload = {
                "attachments": [{
                    "color": color_map.get(record.levelname),
                    "title": f"{record.levelname}!",
                    "fields": [
                        {"title": "MESSAGE", "value": record.message, "short": False},
                        {"title": "TYPE", "value": str(record.exc_info[0]), "short": True},
                        {"title": "VALUE", "value": str(record.exc_info[1]), "short": True},
                        {"title": "TRACEBACK", "value": str(record.exc_info[2]), "short": True},
                        {"title": "FILE", "value": record.filename, "short": True},
                        {"title": "ERROR LINE", "value": record.lineno, "short": True}
                    ],
                    "footer": str(record.__dict__)
                }]
            }
        except Exception:
            payload = {
                "attachments": [{
                    "color": color_map.get(record.levelname),
                    "title": f"{record.levelname}! @everyone",
                    "fields": [
                        {"title": "MESSAGE", "value": record.message, "short": False},
                        {"title": "FILE", "value": record.filename, "short": True},
                        {"title": "ERROR LINE", "value": record.lineno, "short": True}
                    ],
                    "footer": str(record.__dict__)
                }]
            }
        return payload

    def send_to_slack(self, payload):
        headers = {"Content-Type": "application/json"}
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
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }
        color = color_map.get(level, Fore.WHITE)
        print(f"{color}{message}")


class DBLOGHandler(logging.Handler):
    """ MongoDB에 로그를 저장하는 핸들러 """

    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.db_controller = MongoController()

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            threading.Thread(target=self.record_db, args=(record,)).start()
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

        # Remove or convert non-serializable types to string
        for key, value in data.items():
            try:
                # Check if the value can be serialized to BSON (MongoDB format)
                bson.BSON.encode({key: value})
            except Exception:
                # If not serializable, convert to string
                data[key] = str(value)

        try:
            self.db_controller.insert_one("log", data)
            print("Log successfully recorded in DB.")
        except Exception as e:
            print(f"Error recording log to DB: {e}")


def setup_logger():
    logger = logging.getLogger("bestkr_logger")

    # Slack 핸들러 추가
    slack_handler = SlackWebhookHandler()
    slack_handler.setLevel(logging.ERROR)

    discord_handler = DiscordWebhookHandler()
    discord_handler.setLevel(logging.ERROR)
    # DB 핸들러 추가
    db_handler = DBLOGHandler()
    db_handler.setLevel(logging.DEBUG)

    # 핸들러 추가
    logger.addHandler(slack_handler)
    logger.addHandler(db_handler)
    logger.addHandler(discord_handler)

    logger.setLevel(logging.DEBUG)

    if Config.get_env("SERVER_RUN_MODE") == "TRUE":
        return logger
    else:
        log = logging.getLogger()
        log.addHandler(logging.StreamHandler())
        log.setLevel(logging.DEBUG)
        return log


def catch_exception(exc_type, exc_value, exc_traceback):
    if Config.get_env("SERVER_RUN_MODE") == "TRUE":
        logger = setup_logger()
    else:
        logger = logging.getLogger("")
    logger.exception("Unexpected exception.", exc_info=(exc_type, exc_value, exc_traceback))


# SERVER_RUN_MODE 상태 확인을 위한 디버깅 코드
print(f"SERVER_RUN_MODE: {Config().get_env('SERVER_RUN_MODE')}")
