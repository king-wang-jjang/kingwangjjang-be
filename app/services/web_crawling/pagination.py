import graphene
from app.db.mongo_controller import MongoController
from app.utils.loghandler import catch_exception, setup_logger
import sys

# 예외 처리 및 로거 설정
sys.excepthook = catch_exception
logger = setup_logger()

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
    Tag = graphene.List(str)
    def __init__(self, **kwargs):
        kwargs.pop('_id', None)  # '_id' 필드 제거
        super().__init__(**kwargs)


# 페이지 번호를 받아, 30개씩 데이터를 반환하는 함수
def get_pagination_real_time_best(index: int):
    logger.info(f"Fetching real-time best for page index: {index}")

    try:
        data = db_controller.get_real_time_best(index, 30)
        logger.info(f"Successfully fetched {len(data)} records for real-time best.")
        return [BoardSummaryType(**item) for item in data]
    except Exception as e:
        logger.error(f"Error fetching real-time best: {e}")
        return []


def get_pagination_daily_best(index: int):
    logger.info(f"Fetching daily best for page index: {index}")

    try:
        data = db_controller.get_daily_best(index, 30)
        logger.info(f"Successfully fetched {len(data)} records for daily best.")
        return [BoardSummaryType(**item) for item in data]
    except Exception as e:
        logger.error(f"Error fetching daily best: {e}")
        return []
