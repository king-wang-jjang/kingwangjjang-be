import graphene
from graphene import Mutation

from .pagination import BoardSummaryType, paging
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
        # realtime에 gpt answer을 추가 (확장)
        for realtime in realtime_data:
            if realtime_data is None:
                logger.exception(f"GPTAnswer is None")
                continue
            gpt_answer = db_controller.get_gpt(realtime['GPTAnswer'])
            realtime['GPTAnswer'] = gpt_answer

        return realtime_data

    def resolve_all_daily(self, info, **kwargs):
        # insert to Daily
        get_daily_best()
        db_controller = DBController()
        daily_data = db_controller.select('Daily')
        for realtime in daily_data:
            if daily_data is None:
                logger.exception(f"GPTAnswer is None")
                continue
            gpt_answer = db_controller.get_gpt(realtime['GPTAnswer'])
            realtime['GPTAnswer'] = gpt_answer

        return daily_data

class SummaryBoardMutation(Mutation):
    class Arguments:
        board_id = graphene.String(required=True)
        site = graphene.String(required=True)

    board_summary = graphene.String()

    def mutate(self, info, board_id, site):
        _board_summary = board_summary(board_id, site)
        return SummaryBoardMutation(board_summary=_board_summary)

class SummaryBoardByDateMutation(Mutation):
    class Arguments:
        index = graphene.String(required=True)

    board_summaries = graphene.List(BoardSummaryType)

    def mutate(self, info, index):
        try:
            _board_summaries = paging(index) 
        except ValueError:
            raise ValueError("Invalid date format. Please use 'YYYY-MM-DD' format.")

        return SummaryBoardByDateMutation(board_summaries=_board_summaries)


class Mutation(graphene.ObjectType):
    summary_board = SummaryBoardMutation.Field()
    summary_board_by_date = SummaryBoardByDateMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)