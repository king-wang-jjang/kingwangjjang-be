from app import celery_app
from app.services.web_crwaling.index import get_real_time_best


# get_real_time_best를 celery task로 등록하고 주기는 5분으로 설정
@celery_app.task(name='get_real_time_best', bind=True, rate_limit='12/m')
def get_real_time_best(self):
    get_real_time_best()
    return 'success'