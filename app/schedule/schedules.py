import threading
from app.services.web_crawling.index import get_real_time_best
import schedule
import time
def threadings():
    schedule.every(1).minute.do(get_real_time_best)
    while True:
        schedule.run_pending()
        time.sleep(1)
        print("pending")
