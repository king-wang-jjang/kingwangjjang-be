import graphene
from graphene_django.types import DjangoObjectType
from graphene import Mutation

from .views import board_summary, get_real_time_best
from .communityWebsite.models import RealTime, Daily

class RealTimeType(DjangoObjectType):
    class Meta:
        model = RealTime

class DailyType(DjangoObjectType):
    class Meta:
        model = Daily

class Query(graphene.ObjectType):
    all_realtime = graphene.List(RealTimeType)
    all_daily = graphene.List(DailyType)

    def resolve_all_realtime(self, info, **kwargs):
        print(get_real_time_best())
        return RealTime.objects.all()

    def resolve_all_daily(self, info, **kwargs):
        return Daily.objects.all()

class SummaryBoardMutation(Mutation):
    class Arguments:
        board_id = graphene.String(required=True)

    board_summary = graphene.String()

    def mutate(self, info, board_id):
        _board_summary = board_summary(board_id)
        return SummaryBoardMutation(board_summary=_board_summary)

class Mutation(graphene.ObjectType):
    summary_board = SummaryBoardMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
