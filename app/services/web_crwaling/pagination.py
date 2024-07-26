from datetime import datetime, timedelta
import json

import graphene

from app.db.mongo_controller import MongoController

# DBController 인스턴스 생성
db_controller = MongoController()

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
    board_summaries = []
    current_time = datetime.now()
    start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=index) 
    end_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=index - 1) 

    filter = {
        'create_time': {
        '$gte': start_date,
        '$lt': end_date
        }
    }

    realtime_joined_data = db_controller.get_collection('RealTime').aggregate([
        {
            '$match': filter
        },
        {
            '$lookup': {
                'from': 'GPT',
                'localField': 'GPTAnswer',
                'foreignField': '_id', 
                'as': 'GPT'
            }
        }
    ])

    daily_joined_data = db_controller.get_collection('Daily').aggregate([
        {
            '$match': filter
        },
        {
            '$lookup': {
                'from': 'GPT',
                'localField': 'GPTAnswer',
                'foreignField': '_id', 
                'as': 'GPT'
            }
        }
    ])
    for summary in realtime_joined_data:
        answer = summary['GPT'][0]['answer'] if summary['GPT'] else None  
        board_summary = {
            'board_id': summary['board_id'],
            'site': summary['site'],
            'title': summary['title'],
            'url': summary['url'],
            'create_time': summary['create_time'],
            'GPTAnswer': answer
        }
        board_summaries.append(board_summary)

    for summary in daily_joined_data:
        answer = summary['GPT'][0]['answer'] if summary['GPT'] else None  
        board_summary = {
            'board_id': summary['board_id'],
            'rank': summary['rank'],
            'site': summary['site'],
            'title': summary['title'],
            'url': summary['url'],
            'create_time': summary['create_time'],
            'GPTAnswer': answer
        }
        board_summaries.append(board_summary)

    return [BoardSummaryType(**summary) for summary in board_summaries]