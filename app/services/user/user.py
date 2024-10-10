from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from app.utils.oauth import oauth
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import strawberry
from strawberry.fastapi import GraphQLRouter
# from services.web_crwaling.pagination import get_pagination_real_time_best,get_pagination_daily_best
# from services.web_crwaling.views import board_summary,tag
from app.utils.loghandler import setup_logger, catch_exception
from app.db.mongo_controller import MongoController
from faker import Faker
from faker.providers import address, company, date_time, phone_number, person
import sys

# 예외 처리 핸들러
sys.excepthook = catch_exception

# DB 및 Faker 인스턴스
db_controller = MongoController()
fake = Faker('ko_KR')

# 로깅 설정
logger = setup_logger()


def add_user(email: str, name: str):
    """이메일과 이름을 받아 사용자 데이터를 생성 및 삽입하는 함수"""
    logger.debug(f"add_user 호출 - email: {email}, name: {name}")
    try:
        # 사용자 데이터를 생성하고 DB에 삽입
        user_data = {
            'email': email,
            'name': name,
            'nick': fake.user_name(),
            'role': "user"
        }
        logger.debug(f"생성된 사용자 데이터: {user_data}")

        inserted_id = db_controller.insert_one('user', user_data).inserted_id
        logger.info(f"사용자 추가 완료 - inserted_id: {inserted_id}")
        return inserted_id
    except Exception as e:
        logger.exception(f"사용자 추가 중 오류 발생 - email: {email}, 오류: {e}")
        raise HTTPException(status_code=500, detail="사용자 추가 중 오류가 발생했습니다.")


def get_user_by_email(email: str):
    """이메일을 통해 사용자 정보를 조회하는 함수"""
    logger.debug(f"get_user_by_email 호출 - email: {email}")
    try:
        user = db_controller.find('user', {'email': email})[0]
        logger.debug(f"조회된 사용자: {user}")
        return user
    except IndexError:
        logger.warning(f"사용자를 찾을 수 없음 - email: {email}")
        return None
    except Exception as e:
        logger.exception(f"사용자 조회 중 오류 발생 - email: {email}, 오류: {e}")
        raise HTTPException(status_code=500, detail="사용자 조회 중 오류가 발생했습니다.")


def get_user_by_id(id: str):
    """사용자 ID로 사용자 정보를 조회하는 함수"""
    logger.debug(f"get_user_by_id 호출 - id: {id}")
    try:
        user = db_controller.find('user', {'_id': id})[0]
        logger.debug(f"조회된 사용자: {user}")
        return user
    except IndexError:
        logger.warning(f"사용자를 찾을 수 없음 - id: {id}")
        return None
    except Exception as e:
        logger.exception(f"사용자 조회 중 오류 발생 - id: {id}, 오류: {e}")
        raise HTTPException(status_code=500, detail="사용자 조회 중 오류가 발생했습니다.")
