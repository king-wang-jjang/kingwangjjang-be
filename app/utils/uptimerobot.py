import requests
from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception
from app.config import Config
import os
import boto3
url = "https://api.uptimerobot.com/v2/getMonitors"
api_key = Config.get_env("MONITER_API")
payload = f"api_key={api_key}&format=json&logs=1"
headers = {
    'content-type': "application/x-www-form-urlencoded",
    'cache-control': "no-cache"
}


AWS_ACCESS_KEY_ID = Config.get_env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = Config.get_env("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = Config.get_env("AWS_DEFAULT_REGION")
client = boto3.client('s3',
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                      region_name=AWS_DEFAULT_REGION
                      )

def check_online():
    response = requests.request("POST", url, data=payload, headers=headers)
    for i in response.json()["monitors"]:
        if i["status"] != 2:
            response = client.reboot_instances(
                InstanceIds=[
                    Config.get_env("AWS_InstanceIds"),
                ],
                DryRun=False
            )
            return False
    return True
