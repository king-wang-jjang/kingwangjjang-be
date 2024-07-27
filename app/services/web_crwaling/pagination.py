import graphene

from db.mongo_controller import MongoController

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

# 페이지 번호를 받아, 30개씩 데이터를 반환하는 함수
def get_pagination_real_time_best(index: int):
    data = db_controller.get_real_time_best(index, 30)

    return [BoardSummaryType(**item) for item in data]