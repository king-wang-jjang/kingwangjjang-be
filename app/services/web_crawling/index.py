import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
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
from app.constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE, SITE_YGOSU, SITE_PPOMPPU, SITE_THEQOO, SITE_INSTIZ, \
    SITE_RULIWEB
from app.utils.loghandler import setup_logger, catch_exception
import sys

sys.excepthook = catch_exception
logger = setup_logger()

app = FastAPI()
db_controller = MongoController()
board_semaphores = {}
router = APIRouter()


def get_crawler_instance(site: str):
    """
    사이트에 따라 적절한 크롤러 인스턴스를 반환합니다.
    """
    if site == SITE_DCINSIDE:
        return Dcinside()
    elif site == SITE_YGOSU:
        return Ygosu()
    elif site == SITE_PPOMPPU:
        return Ppomppu()
    elif site == SITE_THEQOO:
        return Theqoo()
    elif site == SITE_INSTIZ:
        return Instiz()
    elif site == SITE_RULIWEB:
        return Ruliweb()
    return None


def acquire_semaphore(board_id: str, site: str):
    """
    주어진 게시판 ID와 사이트에 대한 세마포어를 획득합니다.
    """
    global board_semaphores
    semaphore_label = site + board_id

    if semaphore_label not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)

    if not acquired:
        logger.warning(f"Request for {board_id} on site {site} is already being processed.")
        raise HTTPException(status_code=429, detail='요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.')

    return semaphore


def process_content(board_id: str, site: str, is_tag: bool):
    """
    게시글 내용을 가져와 GPT 요약 또는 태그를 생성하고 데이터베이스를 업데이트합니다.
    """
    semaphore = acquire_semaphore(board_id, site)

    try:
        # 데이터베이스에서 실시간 객체 가져오기
        realtime_object = db_controller.find('RealTime', {'board_id': board_id, 'site': site})[0]
        field_name = 'Tag' if is_tag else 'GPTAnswer'
        content_object_id = realtime_object[field_name]

        content_object = db_controller.find(field_name, {'_id': content_object_id})[0]
        if content_object['answer'] != DEFAULT_GPT_ANSWER:
            return content_object['answer']

        crawler_instance = get_crawler_instance(site)
        if not crawler_instance:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 사이트: {site}")

        json_contents = crawler_instance.get_board_contents(board_id)

        str_contents = ''.join([content.get('content', '') for content in json_contents])

        # GPT 요약 또는 태그 처리
        ai_model = Tagsplit() if is_tag else LLM()
        logger.info(f"Processing {('tag' if is_tag else 'summary')} for board {board_id} on site {site}")
        response = ai_model.call(content=str_contents)

        # 결과를 데이터베이스에 업데이트
        db_controller.update_one(field_name, {'_id': content_object_id}, {'$set': {'answer': response}})
        logger.info(f"Document {content_object_id} for board {board_id} on site {site} updated successfully")

        return response

    finally:
        semaphore.release()


def tag(board_id: str, site: str):
    """
    특정 게시글에 대한 태그를 생성합니다.
    """
    return process_content(board_id, site, is_tag=True)


def board_summary(board_id: str, site: str):
    """
    특정 게시글에 대한 요약을 생성합니다.
    """
    return process_content(board_id, site, is_tag=False)


async def board_summary_rest(request: Request):
    """
    REST API 엔드포인트로 게시글 요약을 처리합니다.
    """
    if request.method == 'POST':
        data = await request.json()
        board_id = data.get('board_id')
        site = data.get('site')
        return await board_summary(board_id, site)


def get_real_time_best():
    """
    여러 사이트의 실시간 베스트 게시글을 가져옵니다.
    """
    CrawllerList = [Ygosu(), Ppomppu(), Theqoo(), Instiz(), Ruliweb()]
    for crawler in CrawllerList:
        try:
            crawler.get_real_time_best()
        except Exception as e:
            logger.error(f"Error fetching real-time best: {e}")
    return JSONResponse(content={'response': "실시간 베스트 가져오기 완료"})


def get_daily_best():
    """
    여러 사이트의 데일리 베스트 게시글을 가져옵니다.
    """
    CrawllerList = [Ygosu(), Ppomppu(), Theqoo(), Instiz(), Ruliweb()]
    for crawler in CrawllerList:
        try:
            crawler.get_daily_best()
        except Exception as e:
            logger.error(f"Error fetching daily best: {e}")
    return JSONResponse(content={'response': "데일리 베스트 가져오기 완료"})
