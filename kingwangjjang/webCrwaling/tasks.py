from apscheduler.schedulers.background import BackgroundScheduler
import datetime

from webCrwaling.communityWebsite.dcinside import Dcinside
from webCrwaling.communityWebsite.ygosu import Ygosu

scheduler = BackgroundScheduler()

def real_time_scheduler():
    dcincideCrwaller = Dcinside()
    ygosuCrawller = Ygosu()
    dcincideCrwaller.get_real_time_best()
    ygosuCrawller.get_real_time_best()

now = datetime.datetime.now()
start_minute = 0
# 다음 시간을 체크 하고 적용한다.
if now.minute % 5 == 0:
    start_minute = now.minute
else:
    start_minute = (now.minute // 5 + 1) * 5
    if (start_minute >= 60):
        start_minute = 0

next_date = now.replace(hour=now.hour, minute=start_minute, second=30, microsecond=0)

if next_date < now:
    next_date += datetime.timedelta(hours=1)
    
# Schedule 등록하고 app.py에서 실행
scheduler.add_job(real_time_scheduler, 'interval', minutes=5, start_date=next_date)

