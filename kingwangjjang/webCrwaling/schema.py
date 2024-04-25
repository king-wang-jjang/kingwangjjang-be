import graphene
from graphene import Mutation
from graphene_django.types import DjangoObjectType
from .views import board_summary, get_real_time_best, get_daily_best
from mongo import DBController
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("")

class RealTimeType(graphene.ObjectType):
    board_id = graphene.String()
    site = graphene.String()
    title = graphene.String()
    url = graphene.String()
    create_time = graphene.DateTime()
    GPTAnswer = graphene.String()
    
    def __init__(self, **kwargs):
        kwargs.pop('_id', None)  # '_id' 필드 제거
        super().__init__(**kwargs)

class DailyType(graphene.ObjectType):
    board_id = graphene.String()
    rank = graphene.String()
    site = graphene.String()
    title = graphene.String()
    url = graphene.String()
    create_time = graphene.DateTime()
    GPTAnswer = graphene.String()

    def __init__(self, **kwargs):
        kwargs.pop('_id', None)  # '_id' 필드 제거
        super().__init__(**kwargs)
class Query(graphene.ObjectType):
    all_realtime = graphene.List(RealTimeType)
    all_daily = graphene.List(DailyType)

    def resolve_all_realtime(self, info, **kwargs):
        get_real_time_best()
        db_controller = DBController()
        realtime_data = db_controller.select('RealTime')
        return [RealTimeType(**data) for data in realtime_data]

    def resolve_all_daily(self, info, **kwargs):
        get_daily_best()
        db_controller = DBController()
        daily_data = db_controller.select('Daily')
        return [DailyType(**data) for data in daily_data]

class SummaryBoardMutation(Mutation):
    class Arguments:
        board_id = graphene.String(required=True)
        site = graphene.String(required=True)

    board_summary = graphene.String()

    def mutate(self, info, board_id, site):
        _board_summary = board_summary(board_id, site)
        return SummaryBoardMutation(board_summary=_board_summary)

### 추가 ###

db_controller = DBController()

def get_board_summaries_by_date(date):
        # RealTime 모델에서 해당 날짜의 데이터를 필터링합니다.
        real_time_summaries = db_controller.select('RealTime')
        # Daily 모델에서 해당 날짜의 데이터를 필터링합니다.
        daily_summaries = db_controller.select('Daily') # 이미 있는 Board는 넘기기

        # 필터링된 결과를 하나의 리스트로 결합합니다.
        board_summaries = list(real_time_summaries) + list(daily_summaries)

        # 결과를 반환합니다.
        return [DailyType(**data) for data in board_summaries]

class SummaryBoardByDateMutation(Mutation):
    class Arguments:
        # date = graphene.String(required=True)  # 날짜(형식: 'YYYY-MM-DD')
        index = graphene.String(required=True)

    board_summaries = graphene.List(graphene.String)

    def mutate(self, info, index): # info는 무조건 있어야하는 변수임 -> info가 뭔지 print 해보기
        # 날짜 문자열을 datetime 객체로 변환합니다.
        try:
            # datetime_obj = datetime.now(date, '%Y-%m-%d')
            datetime_obj = datetime.now() - timedelta(days=1)
            # print(datetime_obj)
        except ValueError:
            raise ValueError("Invalid date format. Please use 'YYYY-MM-DD' format.")

        # 해당 날짜의 데이터를 가져오기 위해 적절한 메서드 호출
        board_summaries = get_board_summaries_by_date(datetime_obj) # datetime_obj - 1day

        return SummaryBoardByDateMutation(board_summaries=board_summaries)

### 추가 ###

class Mutation(graphene.ObjectType):
    summary_board = SummaryBoardMutation.Field()
    ## 추가
    summary_board_by_date = SummaryBoardByDateMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)