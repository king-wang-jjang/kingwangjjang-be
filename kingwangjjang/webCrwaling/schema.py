import graphene
from graphene_django.types import DjangoObjectType
from graphene import Mutation

from .views import board_summary
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
        return RealTime.objects.all()

    def resolve_all_daily(self, info, **kwargs):
        return Daily.objects.all()

class SummaryBoardMutation(Mutation):
    class Arguments:
        board_id = graphene.String(required=True)

    response = graphene.String()

    def mutate(self, info, board_id):
        # 요약 보드 함수 호출
        response = board_summary(board_id)
        return SummaryBoardMutation(response=response)

class Mutation(graphene.ObjectType):
    summary_board = SummaryBoardMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
