from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional, Union
from app.db.mongo_controller import MongoController
from app.db.context import Database
from app.graphql.modules.board.board_type import Realtime
from app.utils.loghandler import catch_exception, setup_logger
import sys
from pymongo import UpdateOne

# 예외 처리 및 로거 설정
sys.excepthook = catch_exception
logger = setup_logger()

db_controller = MongoController()


# 페이지 번호를 받아, 30개씩 데이터를 반환하는 함수
def get_pagination_real_time_best(index: int) -> List[Realtime]: 
    logger.info(f"real-time best page index: {index}")
    try:
        collection = Database.get_collection('Realtime')
        data = list(
            collection.find()
            .sort("create_time", -1)
            .skip(index * 30)
            .limit(30)
        )

        # Compute comment counts for these realtime ids and write back to Realtime
        ids = [doc.get("_id") for doc in data if doc.get("_id") is not None]
        id_to_count = {}
        if ids:
            comment_coll = Database.get_collection('Comment')
            agg = comment_coll.aggregate([
                {"$match": {"board_id": {"$in": ids}, "is_deleted": False}},
                {"$group": {"_id": "$board_id", "count": {"$sum": 1}}}
            ])
            for row in agg:
                id_to_count[row.get("_id")] = int(row.get("count", 0))

            # Bulk update Realtime.comment_count
            operations = [
                UpdateOne({"_id": rid}, {"$set": {"comment_count": id_to_count.get(rid, 0)}})
                for rid in ids
            ]
            if operations:
                try:
                    collection.bulk_write(operations, ordered=False)
                except Exception:
                    # Non-fatal: continue to return counts even if write fails
                    pass

        # Like counts are stored directly on Realtime.like_count (no Count collection usage)
        
        def extract_thumbnail(contents):
            """ contents 리스트에서 첫 번째 'image' 타입의 path를 반환 """
            if isinstance(contents, list):
                for item in contents:
                    if item.get("type") == "image":
                        return item.get("path")  # 첫 번째 'image' 타입의 path 반환
            return None  # 'image' 타입이 없으면 None 반환
        
        return [
            Realtime(
                **{k: v for k, v in {**item, "comment_count": id_to_count.get(item.get("_id"), item.get("comment_count", 0))}.items() if k != "like_count"},
                thumbnail=extract_thumbnail(item.get("contents")),
                likeCount=int(item.get("like_count", 0) or 0)
            )
            for item in data
        ]
    
    except Exception as e:
        logger.exception(f"Error getting realtime data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
def get_pagination_daily_best(index: int) -> List[Realtime]:
    logger.info(f"daily page index: {index}")

    try:
        data = db_controller.get_daily_best(index, 30)
        logger.info(f"Successfully fetched {len(data)} records for daily best.")
        return [
            Realtime(
                **{k: v for k, v in item.items() if k != "like_count"},
                likeCount=int(item.get("like_count", 0) or 0)
            )
            for item in data
        ]
    except Exception as e:
        logger.exception(f"Error getting daily data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
