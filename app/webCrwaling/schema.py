import os
from bs4 import BeautifulSoup
import requests
from constants import SITE_DCINSIDE, SITE_PPOMPPU, SITE_YGOSU

import graphene
from graphene import Mutation

from .pagination import BoardSummaryType, get_page_data_by_index
from .views import board_summary, get_real_time_best, get_daily_best
from mongo import DBController
from datetime import datetime, timedelta
import logging
from .tasks import task_add

logger = logging.getLogger("")

# class RealTimeType(graphene.ObjectType):
#     board_id = graphene.String()
#     site = graphene.String()
#     title = graphene.String()
#     url = graphene.String()
#     create_time = graphene.DateTime()
#     GPTAnswer = graphene.String()
    
#     def __init__(self, **kwargs):
#         kwargs.pop('_id', None)  # '_id' 필드 제거
#         super().__init__(**kwargs)


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
    # all_realtime = graphene.List(RealTimeType)
    all_daily = graphene.List(DailyType)
    board_contents_by_date = graphene.List(BoardSummaryType, index=graphene.String(required=True))

    def resolve_all_realtime(self, info, **kwargs):
        db_controller = DBController()
        realtime_data = db_controller.select('RealTime')
        # realtime(에 gpt answer을 추가 (확장)
        for realtime in realtime_data:
            if realtime_data is None:
                logger.exception(f"GPTAnswer is None")
                continue
            gpt_answer = db_controller.get_gpt(realtime['GPTAnswer'])
            realtime['GPTAnswer'] = gpt_answer

        return realtime_data

    def resolve_all_daily(self, info, **kwargs):
        print(task_add.delay(1, 2))

        # db_controller = DBController()
        # daily_data = db_controller.select('Daily')
        # for realtime in daily_data:
        #     if daily_data is None:
        #         logger.exception(f"GPTAnswer is None")
        #         continue
        #     gpt_answer = db_controller.get_gpt(realtime['GPTAnswer'])
        #     realtime['GPTAnswer'] = gpt_answer

        # return daily_data

    def resolve_board_contents_by_date(self, info, index):
        board_summaries = get_page_data_by_index(index) 

        return board_summaries

class SummaryBoardMutation(Mutation):
    class Arguments:
        board_id = graphene.String(required=True)
        site = graphene.String(required=True)

    board_summary = graphene.String()

    def mutate(self, info, board_id, site):
        _board_summary = board_summary(board_id, site)
        return SummaryBoardMutation(board_summary=_board_summary)


class Mutation(graphene.ObjectType):
    summary_board = SummaryBoardMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

