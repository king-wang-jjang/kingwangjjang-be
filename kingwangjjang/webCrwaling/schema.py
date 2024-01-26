# schema.py

import graphene
from graphene_django.types import DjangoObjectType

from mongo import DBController
from .models import RealTime, Daily

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
        print("RealTime.objects.all()", RealTime.objects.all())
        return RealTime.objects.all()

    def resolve_all_daily(self, info, **kwargs):
        return Daily.objects.all()

schema = graphene.Schema(query=Query)