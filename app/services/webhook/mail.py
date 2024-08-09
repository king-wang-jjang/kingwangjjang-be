from config import Config
import requests
class Mail_webhooks():
    def __init__(self):
        self.webhook_url = Config.get_env("MAIL_WEBHOOK_URL")
    def create_payload(self,basemodels, db_id):
        payload = {
            "attachments": [
                {
                    "color": "#00FF00",
                    "title": f"새로운 매일이 도착했습니다!",
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
                            "short": True
                        }
                    ],
                    "footer": f"DB ID : {db_id}"
                }
            ]
        }
        return payload
    def send_slack(self, payload):
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending log to Slack: {e}")