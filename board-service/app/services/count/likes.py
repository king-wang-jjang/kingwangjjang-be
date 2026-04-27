import logging
from fastapi import HTTPException
from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger, catch_exception
import sys
from typing import Dict, Any

# 예외 핸들러 설정
sys.excepthook = catch_exception

# 로거 설정
logger = setup_logger()

# MongoController 인스턴스
db_controller = MongoController()


def get_likes_info(board_id: str, site: str, user_id: str = None) -> Dict[str, Any]:
    """
    게시판 ID와 사이트를 기반으로 좋아요 정보(총 수, 현재 사용자의 좋아요 여부)를 반환합니다.
    """
    logger.debug(f"get_likes_info 호출 - board_id: {board_id}, site: {site}, user_id: {user_id}")

    try:
        query = {'board_id': board_id, 'site': site}
        count_object = db_controller.find_one('Count', query)

        if not count_object:
            logger.warning(f"Count 객체가 없음 - board_id: {board_id}, site: {site}. 새로 생성합니다.")
            # 데이터가 없을 경우 새로 생성
            new_doc = {'board_id': board_id, 'site': site, 'likes': 0, 'views': 0, 'liked_by': []}
            db_controller.insert_one('Count', new_doc)
            return {'total_likes': 0, 'is_liked': False}

        total_likes = count_object.get('likes', 0)
        liked_by_list = count_object.get('liked_by', [])
        is_liked = user_id in liked_by_list if user_id else False

        return {'total_likes': total_likes, 'is_liked': is_liked}

    except Exception as e:
        logger.exception(f"좋아요 정보 조회 중 오류 발생 - board_id: {board_id}, site: {site}, 오류: {e}")
        raise HTTPException(status_code=500, detail="좋아요 정보 조회 중 오류가 발생했습니다.")


def toggle_like(board_id: str, site: str, user_id: str):
    """
    사용자의 '좋아요' 상태를 토글합니다. (좋아요 추가 또는 취소)
    """
    logger.debug(f"toggle_like 호출 - board_id: {board_id}, site: {site}, user_id: {user_id}")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="좋아요를 누르려면 로그인이 필요합니다.")

    try:
        query = {'board_id': board_id, 'site': site}
        count_object = db_controller.find_one('Count', query)

        if not count_object:
            # 문서가 없으면 새로 생성하며 좋아요 추가
            logger.warning(f"Count 객체가 없음 - board_id: {board_id}, site: {site}. 새로 생성하며 좋아요를 추가합니다.")
            new_doc = {'board_id': board_id, 'site': site, 'likes': 1, 'views': 0, 'liked_by': [user_id]}
            db_controller.insert_one('Count', new_doc)
            return {'total_likes': 1, 'is_liked': True}

        liked_by_list = count_object.get('liked_by', [])
        
        if user_id in liked_by_list:
            # 이미 좋아요를 눌렀으면 취소
            update = {
                '$inc': {'likes': -1},
                '$pull': {'liked_by': user_id}
            }
            db_controller.update_one(collection_name='Count', query=query, update=update)
            
            new_total_likes = count_object.get('likes', 1) - 1
            logger.info(f"좋아요 취소 - board_id: {board_id}, user_id: {user_id}")
            return {'total_likes': new_total_likes, 'is_liked': False}
        else:
            # 좋아요를 누르지 않았으면 추가
            update = {
                '$inc': {'likes': 1},
                '$push': {'liked_by': user_id}
            }
            db_controller.update_one(collection_name='Count', query=query, update=update)
            
            new_total_likes = count_object.get('likes', 0) + 1
            logger.info(f"좋아요 추가 - board_id: {board_id}, user_id: {user_id}")
            return {'total_likes': new_total_likes, 'is_liked': True}

    except Exception as e:
        logger.exception(f"좋아요 토글 중 오류 발생 - board_id: {board_id}, site: {site}, user_id: {user_id}, 오류: {e}")
        raise HTTPException(status_code=500, detail="좋아요 처리 중 오류가 발생했습니다.")