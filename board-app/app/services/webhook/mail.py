from app.config import Config
import requests
from app.utils.loghandler import setup_logger, catch_exception
import sys

# Set up global exception handling and logger
sys.excepthook = catch_exception
logger = setup_logger()

class MailWebhooks:
    def __init__(self):
        self.webhook_url = Config.get_env("MAIL_WEBHOOK_URL")

    def create_payload(self, basemodels, db_id):
        """
        Create the payload for Slack webhook notification.
        """
        payload = {
            "attachments": [
                {
                    "color": "#00FF00",
                    "title": "새로운 매일이 도착했습니다!",
                    "fields": [
                        {
                            "title": "발신자",
                            "value": f"{basemodels.FromName} ({basemodels.From})",
                            "short": True
                        },
                        {
                            "title": "수신자",
                            "value": basemodels.To,
                            "short": True
                        },
                        {
                            "title": "제목",
                            "value": basemodels.Subject,
                            "short": True
                        },
                        {
                            "title": "내용",
                            "value": basemodels.TextBody,
                            "short": False
                        }
                    ],
                    "footer": f"DB ID : {db_id}"
                }
            ]
        }
        logger.debug(f"Mail | Payload created: {payload}")
        return payload

    def send_slack(self, payload):
        """
        Send the payload to Slack via webhook.
        """
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for non-2xx responses
            logger.info(f"Mail | Slack notification sent successfully: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Mail | Error sending notification to Slack: {e}")
