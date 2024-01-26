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
        db_controller = DBController()
        db_handle, _ = db_controller.GetDBHandle()
        collection = db_handle['pymongotest']  # 여기서 'your_collection_name'은 실제 MongoDB 컬렉션의 이름으로 바꿔주세요
        # data = list(collection.find())
        data = db_controller.select("pymongotest")
  
        return [RealTimeType(**item) for item in data]

    def resolve_all_daily(self, info, **kwargs):
        return Daily.objects.all()

schema = graphene.Schema(query=Query)