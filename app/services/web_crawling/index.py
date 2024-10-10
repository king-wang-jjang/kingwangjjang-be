import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings

from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.instiz import Instiz
from app.services.web_crawling.community_website.ppomppu import Ppomppu
from app.services.web_crawling.community_website.ruliweb import Ruliweb
from app.services.web_crawling.community_website.theqoo import Theqoo
from app.services.web_crawling.community_website.ygosu import Ygosu
from app.services.web_crawling.community_website.dcinside import Dcinside

from app.utils.llm import LLM
from app.utils.tag_split import Tagsplit

from app.constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE, SITE_YGOSU, SITE_PPOMPPU, SITE_THEQOO, SITE_INSTIZ, SITE_RULIWEB
from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
logger = setup_logger()

app = FastAPI()

board_semaphores = {}
db_controller = MongoController()

router = APIRouter()

def tag(board_id: str, site: str):
    global board_semaphores
    semaphore_label = site + board_id

    logger.debug(f"tag 함수 실행 - board_id: {board_id}, site: {site}")

    if semaphore_label not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)
        logger.debug(f"새로운 세마포어 생성 - semaphore_label: {semaphore_label}")

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)
    if not acquired:
        logger.warning(f"세마포어 획득 실패 - board_id: {board_id}, site: {site}")
        raise HTTPException(status_code=429, detail='요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.')

    try:
        realtime_object = db_controller.find('RealTime', {'board_id': board_id, 'site': site})[0]
        TAG_Object_id = realtime_object['Tag']
        TAG_object = db_controller.find('Tag', {'_id': TAG_Object_id})[0]

        logger.debug(f"DB 조회 결과 - TAG_Object_id: {TAG_Object_id}, TAG_object: {TAG_object}")

        if TAG_object['tag'] != DEFAULT_GPT_ANSWER:
            logger.info(f"이미 처리된 TAG 반환 - tag: {TAG_object['tag']}")
            return TAG_object['tag']

        # 사이트에 따른 크롤러 인스턴스 생성
        if site == SITE_DCINSIDE:
            crawler_instance = Dcinside()
        elif site == SITE_YGOSU:
            crawler_instance = Ygosu()
        elif site == SITE_PPOMPPU:
            crawler_instance = Ppomppu()
        elif site == SITE_THEQOO:
            crawler_instance = Theqoo()
        elif site == SITE_INSTIZ:
            crawler_instance = Instiz()
        elif site == SITE_RULIWEB:
            crawler_instance = Ruliweb()
        else:
            crawler_instance = None

        logger.debug(f"크롤러 인스턴스 생성 - crawler_instance: {crawler_instance}")

        json_contents = crawler_instance.get_board_contents(board_id)
        logger.debug(f"크롤러에서 가져온 게시판 내용 - json_contents: {json_contents}")

        str_contents = ''
        for content in json_contents:
            if 'content' in content:
                str_contents += content['content']

        logger.debug(f"게시판 내용을 문자열로 변환 - str_contents: {str_contents}")

        # GPT 요약 요청
        chatGPT = Tagsplit()
        logger.info(f"GPT 요약 요청 URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id)
        response = chatGPT.call(content=str_contents)
        logger.debug(f"GPT 응답 결과 - response: {response}")

        # DB 업데이트
        if TAG_object:
            db_controller.update_one('GPT', {'_id': TAG_Object_id}, {'$set': {'answer': response}})
            logger.info(f"문서 업데이트 완료 - TAG_Object_id: {TAG_Object_id}, site: {site}, board_id: {board_id}")
        else:
            logger.error(f"문서 조회 실패 - TAG_Object_id: {TAG_Object_id}, site: {site}, board_id: {board_id}")
            return JSONResponse(content={"detail": "해당 ObjectId로 문서를 찾을 수 없습니다."}, status_code=404)

        return response

    except Exception as e:
        logger.exception(f"예외 발생 - board_id: {board_id}, site: {site}")
        raise e

    finally:
        semaphore.release()
        logger.debug(f"세마포어 해제 - board_id: {board_id}, site: {site}")


def board_summary(board_id: str, site: str):
    global board_semaphores
    semaphore_label = site + board_id

    logger.debug(f"board_summary 함수 실행 - board_id: {board_id}, site: {site}")

    if semaphore_label not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)
        logger.debug(f"새로운 세마포어 생성 - semaphore_label: {semaphore_label}")

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)
    if not acquired:
        logger.warning(f"세마포어 획득 실패 - board_id: {board_id}, site: {site}")
        raise HTTPException(status_code=429, detail='요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.')

    try:
        realtime_object = db_controller.find('RealTime', {'board_id': board_id, 'site': site})[0]
        GPT_Object_id = realtime_object['GPTAnswer']
        GPT_object = db_controller.find('GPT', {'_id': GPT_Object_id})[0]

        logger.debug(f"DB 조회 결과 - GPT_Object_id: {GPT_Object_id}, GPT_object: {GPT_object}")

        if GPT_object['answer'] != DEFAULT_GPT_ANSWER:
            logger.info(f"이미 처리된 GPT 답변 반환 - answer: {GPT_object['answer']}")
            return GPT_object['answer']

        # 사이트에 따른 크롤러 인스턴스 생성
        if site == SITE_DCINSIDE:
            crawler_instance = Dcinside()
        elif site == SITE_YGOSU:
            crawler_instance = Ygosu()
        elif site == SITE_PPOMPPU:
            crawler_instance = Ppomppu()
        elif site == SITE_THEQOO:
            crawler_instance = Theqoo()
        elif site == SITE_INSTIZ:
            crawler_instance = Instiz()
        elif site == SITE_RULIWEB:
            crawler_instance = Ruliweb()
        else:
            crawler_instance = None

        logger.debug(f"크롤러 인스턴스 생성 - crawler_instance: {crawler_instance}")

        json_contents = crawler_instance.get_board_contents(board_id)
        logger.debug(f"크롤러에서 가져온 게시판 내용 - json_contents: {json_contents}")

        str_contents = ''
        for content in json_contents:
            if 'content' in content:
                str_contents += content['content']

        logger.debug(f"게시판 내용을 문자열로 변환 - str_contents: {str_contents}")

        # GPT 요약 요청
        chatGPT = LLM()
        logger.info(f"GPT 요약 요청 URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id)
        response = chatGPT.call(content=str_contents)
        logger.debug(f"GPT 응답 결과 - response: {response}")

        # DB 업데이트
        if GPT_object:
            db_controller.update_one('GPT', {'_id': GPT_Object_id}, {'$set': {'answer': response}})
            logger.info(f"문서 업데이트 완료 - GPT_Object_id: {GPT_Object_id}, site: {site}, board_id: {board_id}")
        else:
            logger.error(f"문서 조회 실패 - GPT_Object_id: {GPT_Object_id}, site: {site}, board_id: {board_id}")
            return JSONResponse(content={"detail": "해당 ObjectId로 문서를 찾을 수 없습니다."}, status_code=404)

        return response

    except Exception as e:
        logger.exception(f"예외 발생 - board_id: {board_id}, site: {site}")
        raise e

    finally:
        semaphore.release()
        logger.debug(f"세마포어 해제 - board_id: {board_id}, site: {site}")


def get_real_time_best():
    CrawllerList = [Ygosu(), Ppomppu(), Theqoo(), Instiz(), Ruliweb()]

    for crawler in CrawllerList:
        if crawler is None:
            logger.warning(f"Skipping null crawler in list.")
            continue

        try:
            logger.info(f"Starting real-time best fetch from {crawler.__class__.__name__}")
            crawler.get_real_time_best()
            logger.info(f"Successfully fetched real-time best from {crawler.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error fetching real-time best from {crawler.__class__.__name__}: {str(e)}", exc_info=True)

    return JSONResponse(content={'response': "실시간 베스트 가져오기 완료"})


def get_daily_best():
    CrawllerList = [Ygosu(), Ppomppu(), Theqoo(), Instiz(), Ruliweb()]

    for crawler in CrawllerList:
        if crawler is None:
            logger.warning(f"Skipping null crawler in list.")
            continue

        try:
            logger.info(f"Starting daily best fetch from {crawler.__class__.__name__}")
            crawler.get_daily_best()
            logger.info(f"Successfully fetched daily best from {crawler.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error fetching daily best from {crawler.__class__.__name__}: {str(e)}", exc_info=True)

    return JSONResponse(content={'response': "데일리 베스트 가져오기 완료"})

