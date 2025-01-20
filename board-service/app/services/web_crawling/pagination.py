from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional, Union
from app.db.mongo_controller import MongoController
from app.types.board_type import Realtime
from app.utils.loghandler import catch_exception, setup_logger
import sys

# 예외 처리 및 로거 설정
sys.excepthook = catch_exception
logger = setup_logger()

db_controller = MongoController()


# 페이지 번호를 받아, 30개씩 데이터를 반환하는 함수
def get_pagination_real_time_best(index: int) -> List[Realtime]:
    logger.info(f"real-time best page index: {index}")

    try:
        data = db_controller.get_real_time_best(index, 30)
        logger.info(f"Successfully fetched {len(data)} records for real-time best.")

        return [Realtime(**item) for item in data]
    except Exception as e:
        logger.exception(f"Error getting realtime data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
def get_pagination_daily_best(index: int) -> List[Realtime]:
    logger.info(f"daily page index: {index}")

    try:
        data = db_controller.get_daily_best(index, 30)
        logger.info(f"Successfully fetched {len(data)} records for daily best.")
        return [Realtime(**item) for item in data]
    except Exception as e:
        logger.exception(f"Error getting daily data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
