import logging
from logging import handlers
import os
import sys
import requests
from config import Config
from colorama import Fore, Style, init
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
init(autoreset=True)  # colorama 초기화

class DiscordWebhookHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            self.webhook_url = Config().get_env("WEBHOOK_URL")

    def emit(self, record):
        log_entry = self.format(record)
        if Config().get_env("SERVER_RUN_MODE") == "TRUE":
            embed = self.create_embed(record)
            self.send_to_discord(embed)
        else:
            self.print_colored_log(log_entry, record.levelname)


    def create_embed(self, record):
        color_map = {
            "DEBUG": 0x808080,   # Gray
            "INFO": 0x00FF00,    # Green
            "WARNING": 0xFFFF00, # Yellow
            "ERROR": 0xFF0000,   # Red
            "CRITICAL": 0x8B0000 # Dark Red
        }
        try:
            embed = {
                "title": record.levelname,
                "fields": [
                    {
                        "name": "MESSAGE",
                        "value": record.message
                    },
                    {
                        "name": "TYPE",
                        "value": record.exc_info[0],
                        "inline": True
                    },
                    {
                        "name": "VALUE",
                        "value" : record.exc_info[1],
                        "inline": True
                    },
                    {
                        "name": "TRACEBACK",
                        "value": record.exc_info[2],
                        "inline": True
                    },
                    {
                        "name": "FILE",
                        "value": record.filename,
                        "inline": True
                    },
                    {
                        "name": "ERROR LINE",
                        "value": record.lineno,
                        "inline": True
                    }
                ],
                "footer": {
                    "text": record.__dict
                },
                "color" : color_map.get(record.levelname)
            }
        except Exception as e:
            embed = {
                "title": record.levelname,
                "fields": [
                    {
                        "name": "MESSAGE",
                        "value": record.message
                    },
                    {
                        "name": "FILE",
                        "value": record.filename,
                        "inline": True
                    },
                    {
                        "name": "ERROR LINE",
                        "value": record.lineno,
                        "inline": True
                    }
                ],
                "footer": {
                    "text": str(record.__dict__)
                },
                "color": color_map.get(record.levelname)
            }
        return embed

    def send_to_discord(self, embed):
        payload = {
            "embeds": [embed]
        }
        headers = {
            "Content-Type": "application/json"
        }
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
            "CRITICAL": Fore.RED + Style.BRIGHT
        }
        color = color_map.get(level, Fore.WHITE)  # Default to white if level not found
        print(f"{color}{message}")

def setup_logger():
    logger = logging.getLogger("discord_logger")
    logger.setLevel(logging.ERROR)  # ERROR 레벨까지 모든 로그를 처리

    # 디스코드 웹훅 핸들러 추가
    discord_handler = DiscordWebhookHandler()
    discord_handler.setLevel(logging.ERROR)  # ERROR 레벨까지 모든 로그를 처리

    # 로그 메시지 형식 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    discord_handler.setFormatter(formatter)

    # 핸들러를 로거에 추가
    logger.addHandler(discord_handler)

    return logger
def catch_exception(exc_type, exc_value, exc_traceback):

    # 로깅 모듈을 이용해 로거를 미리 등록해놔야 합니다.
    logger = logging.getLogger("discord_logger")
    logger.error("Unexpected exception.",exc_info=(exc_type, exc_value, exc_traceback))
