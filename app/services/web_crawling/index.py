import graphene
from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger, catch_exception
import sys

# 시스템 예외처리 핸들러 설정
sys.excepthook = catch_exception

# 로거 설정
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

    def __init__(self, **kwargs):
        logger.debug(f"BoardSummaryType 초기화 - kwargs: {kwargs}")
        kwargs.pop('_id', None)  # '_id' 필드 제거
        super().__init__(**kwargs)


# 페이지 번호를 받아, 30개씩 데이터를 반환하는 함수
def get_pagination_real_time_best(index: int):
    logger.debug(f"get_pagination_real_time_best 호출 - index: {index}")

    try:
        data = db_controller.get_real_time_best(index, 30)
        logger.debug(f"실시간 베스트 데이터 조회 성공 - data 길이: {len(data)}")
        return [BoardSummaryType(**item) for item in data]
    except Exception as e:
        logger.exception(f"실시간 베스트 데이터 조회 중 오류 발생 - index: {index}, 오류: {e}")
        raise


def get_pagination_daily_best(index: int):
    logger.debug(f"get_pagination_daily_best 호출 - index: {index}")

    try:
        data = db_controller.get_daily_best(index, 30)
        logger.debug(f"데일리 베스트 데이터 조회 성공 - data 길이: {len(data)}")
        return [BoardSummaryType(**item) for item in data]
    except Exception as e:
        logger.exception(f"데일리 베스트 데이터 조회 중 오류 발생 - index: {index}, 오류: {e}")
        raise
