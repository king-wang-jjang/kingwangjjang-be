from datetime import datetime, timedelta
import json

import graphene
from mongo import DBController

# DBController 인스턴스 생성
db_controller = DBController()

class BoardSummaryType(graphene.ObjectType):
    board_id = graphene.String()
    site = graphene.String()
    rank = graphene.String()
    title = graphene.String()
    url = graphene.String()
    create_time = graphene.DateTime()
    GPTAnswer = graphene.String()

    def __init__(self, **kwargs):
        kwargs.pop('_id', None)  # '_id' 필드 제거
        super().__init__(**kwargs)

# 페이지 번호를 받아, create_time이 (오늘 날짜 - 페이지 번호)에 해당하는 데이터 파싱
def get_page_data_by_index(index: str):
    index = int(index)

    current_time = datetime.now()
    start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=index) 
    end_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=index - 1) 

    filter = {
        'create_time': {
        '$gte': start_date,
        '$lt': end_date
        }
    }
    real_time_summaries = db_controller.select('RealTime', filter)
    daily_summaries = db_controller.select('Daily', filter)
    board_summaries = list(real_time_summaries) + list(daily_summaries)

    return [BoardSummaryType(**{**summary, 'GPTAnswer': db_controller.get_gpt(summary['GPTAnswer'])}) for summary in board_summaries]