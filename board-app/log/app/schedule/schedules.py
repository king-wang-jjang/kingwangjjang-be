import threading
import time

import schedule

from app.services.web_crawling.index import get_real_time_best


def threadings():
    """ """
    schedule.every(10).seconds.do(get_real_time_best)
    while True:
        schedule.run_pending()
        time.sleep(1)
        print("pending")
