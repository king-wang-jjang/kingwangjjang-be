from logging import handlers
import logging
import os
import sys
from config import Config
import requests
class DiscordWebhookHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.webhook_url = Config().get("WEBHOOK_URL")

    def emit(self, record):
        log_entry = self.format(record)
        embed = self.create_embed(log_entry, record.levelname)
        self.send_to_discord(embed)

    def create_embed(self, message, level):
        color_map = {
            "DEBUG": 0x808080,   # Gray
            "INFO": 0x00FF00,    # Green
            "WARNING": 0xFFFF00, # Yellow
            "ERROR": 0xFF0000,   # Red
            "CRITICAL": 0x8B0000 # Dark Red
        }
        embed = {
            "title": f"Log - {level}",
            "description": message,
            "color": color_map.get(level, 0x000000) # Default to black if level not found
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

def setup_logger():
    logger = logging.getLogger("discord_logger")
    logger.setLevel(logging.DEBUG)  # DEBUG 레벨까지 모든 로그를 처리

    # 디스코드 웹훅 핸들러 추가
    discord_handler = DiscordWebhookHandler()
    discord_handler.setLevel(logging.DEBUG)  # DEBUG 레벨까지 모든 로그를 처리

    # 로그 메시지 형식 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    discord_handler.setFormatter(formatter)

    # 핸들러를 로거에 추가
    logger.addHandler(discord_handler)

    return logger
