from datetime import datetime, timedelta
from mongo import DBController
from schema import DailyType, RealTimeType

# DBController 인스턴스 생성
db_controller = DBController()

def paging(filter):
    # RealTime 모델에서 해당 날짜의 데이터를 필터링합니다.
    real_time_summaries = db_controller.select('RealTime', filter)

    # Daily 모델에서 해당 날짜의 데이터를 필터링합니다.
    daily_summaries = db_controller.select('Daily', filter) # 이미 있는 Board는 넘기기

    # 필터링된 결과를 하나의 리스트로 결합합니다.
    board_summaries = list(real_time_summaries) + list(daily_summaries)

    # 결과를 반환합니다.
    return [DailyType(**data) for data in board_summaries]

# 테스트를 위한 필터링 조건 설정 (예: 현재 날짜의 1일 전 데이터 검색)
filter = {
    'create_time': {
        '$gte': datetime.now() - timedelta(days=1),
        '$lt': datetime.now()
    }
}

# 페이징 함수 호출하여 데이터 검색
result = paging(filter)
