import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings, MongoClient

from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger, catch_exception
import sys

# 예외 핸들러 설정
sys.excepthook = catch_exception

# 로거 설정
logger = setup_logger()

# MongoController 인스턴스
db_controller = MongoController()


def add_views(board_id: str, site: str):
    """게시판 ID와 사이트를 기반으로 조회 수를 증가시키는 함수"""
    logger.debug(f"add_views 호출 - board_id: {board_id}, site: {site}")

    try:
        # Count 컬렉션에서 해당 board_id와 site에 맞는 데이터를 조회
        count_object = db_controller.find('Count', {'board_id': board_id, 'site': site})[0]
        logger.debug(f"조회된 Count 객체: {count_object}")

        # 조회 수(view) 증가
        new_view_count = count_object['views'] + 1
        db_controller.update_one('Count',
                                 {'_id': count_object['_id']},
                                 {'$set': {'views': new_view_count}})
        logger.info(f"조회 수 업데이트 완료 - new_view_count: {new_view_count}")
        return new_view_count

    except IndexError as e:
        # 데이터가 없을 경우 새로 생성
        logger.warning(f"Count 객체가 없음 - board_id: {board_id}, site: {site}, 오류: {e}")
        count_object = db_controller.insert_one('Count', {'board_id': board_id, 'site': site, 'likes': 0, 'views': 1})
        logger.info(f"새 Count 객체 생성 - count_object_id: {count_object.inserted_id}")
        return 1

    except Exception as e:
        logger.exception(f"조회 수 추가 중 오류 발생 - board_id: {board_id}, site: {site}, 오류: {e}")
        raise HTTPException(status_code=500, detail="조회 수 추가 중 오류가 발생했습니다.")


def get_views(board_id: str, site: str):
    """게시판 ID와 사이트를 기반으로 조회 수를 반환하는 함수"""
    logger.debug(f"get_views 호출 - board_id: {board_id}, site: {site}")

    try:
        # Count 컬렉션에서 해당 board_id와 site에 맞는 데이터를 조회
        count_object = db_controller.find('Count', {'board_id': board_id, 'site': site})[0]
        logger.debug(f"조회된 Count 객체: {count_object}")
        return count_object['views']

    except IndexError:
        # 데이터가 없을 경우 조회 수 0으로 새로 생성
        logger.warning(f"Count 객체가 없음 - board_id: {board_id}, site: {site}")
        db_controller.insert_one('Count', {'board_id': board_id, 'site': site, 'likes': 0, 'views': 0})
        return 0

    except Exception as e:
        logger.exception(f"조회 수 조회 중 오류 발생 - board_id: {board_id}, site: {site}, 오류: {e}")
        raise HTTPException(status_code=500, detail="조회 수 조회 중 오류가 발생했습니다.")
