import logging
import sys
import threading

from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import settings

from app.constants import DEFAULT_GPT_ANSWER
from app.constants import SITE_DCINSIDE
from app.constants import SITE_INSTIZ
from app.constants import SITE_PPOMPPU
from app.constants import SITE_RULIWEB
from app.constants import SITE_THEQOO
from app.constants import SITE_YGOSU
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.dcinside import Dcinside
from app.services.web_crawling.community_website.instiz import Instiz
from app.services.web_crawling.community_website.ppomppu import Ppomppu
from app.services.web_crawling.community_website.ruliweb import Ruliweb
from app.services.web_crawling.community_website.theqoo import Theqoo
from app.services.web_crawling.community_website.ygosu import Ygosu
from app.utils.llm import LLM
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger
from app.utils.tag_split import Tagsplit

sys.excepthook = catch_exception
logger = setup_logger()

app = FastAPI()

board_semaphores = {}
db_controller = MongoController()

router = APIRouter()


def tag(board_id: str, site: str):
    """

    :param board_id: str:
    :param site: str:

    """
    global board_semaphores
    semaphore_label = site + board_id

    if board_id not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)
    if not acquired:
        raise HTTPException(
            status_code=429,
            detail="요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.",
        )

    try:
        realtime_object = db_controller.find(
            "RealTime", {"board_id": board_id, "site": site}
        )[0]
        TAG_Object_id = realtime_object["Tag"]
        TAG_object = db_controller.find("Tag", {"_id": TAG_Object_id})[0]

        if TAG_object["tag"] != DEFAULT_GPT_ANSWER:
            return TAG_object["tag"]

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
        json_contents = crawler_instance.get_board_contents(board_id)

        str_contents = ""
        for content in json_contents:
            if "content" in content:
                str_contents += content["content"]
        response = str_contents

        # GPT 요약
        chatGPT = Tagsplit()
        logger.info(
            "URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id
        )
        response = chatGPT.call(content=str_contents)

        # Update answer
        if TAG_object:
            db_controller.update_one(
                "GPT", {"_id": TAG_Object_id}, {"$set": {"answer": response}}
            )
            logger.info(
                f"{TAG_Object_id} site: {site} board_id: {board_id}문서 업데이트 완료"
            )
        else:
            logger.error(
                f"{TAG_Object_id} site: {site} board_id: {board_id}해당 ObjectId로 문서를 찾을 수 없습니다."
            )
            return JSONResponse(
                content={"detail": "해당 ObjectId로 문서를 찾을 수 없습니다."},
                status_code=404,
            )

        return response
    finally:
        semaphore.release()


def board_summary(board_id: str, site: str):
    """

    :param board_id: str:
    :param site: str:

    """
    global board_semaphores
    semaphore_label = site + board_id

    if board_id not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)
    if not acquired:
        raise HTTPException(
            status_code=429,
            detail="요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.",
        )

    try:
        realtime_object = db_controller.find(
            "RealTime", {"board_id": board_id, "site": site}
        )[0]
        GPT_Object_id = realtime_object["GPTAnswer"]
        GPT_object = db_controller.find("GPT", {"_id": GPT_Object_id})[0]

        if GPT_object["answer"] != DEFAULT_GPT_ANSWER:
            return GPT_object["answer"]

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
        json_contents = crawler_instance.get_board_contents(board_id)

        str_contents = ""
        for content in json_contents:
            if "content" in content:
                str_contents += content["content"]
        response = str_contents

        # GPT 요약
        chatGPT = LLM()
        logger.info(
            "URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id
        )
        response = chatGPT.call(content=str_contents)

        # Update answer
        if GPT_object:
            db_controller.update_one(
                "GPT", {"_id": GPT_Object_id}, {"$set": {"answer": response}}
            )
            logger.info(
                f"{GPT_Object_id} site: {site} board_id: {board_id}문서 업데이트 완료"
            )
        else:
            logger.error(
                f"{GPT_Object_id} site: {site} board_id: {board_id}해당 ObjectId로 문서를 찾을 수 없습니다."
            )
            return JSONResponse(
                content={"detail": "해당 ObjectId로 문서를 찾을 수 없습니다."},
                status_code=404,
            )

        return response
    finally:
        semaphore.release()


async def board_summary_rest(request: Request):
    if request.method == "POST":
        data = await request.json()
        board_id = data.get("board_id")
        site = data.get("site")

        return await board_summary(board_id, site)
    # else:
    #     dcincideCrwaller = Dcinside()
    #     dcincideCrwaller.get_real_time_best()

    # return JSONResponse(content={'response': "성공하는 루트 추가해야함"})


def get_real_time_best():
    """ """
    CrawllerList = [Ygosu(), Ppomppu(), Theqoo(), Instiz(), Ruliweb()]
    for i in CrawllerList:
        try:
            i.get_real_time_best()
        except Exception as e:
            logger.error(e)
    return JSONResponse(content={"response": "실시간 베스트 가져오기 완료"})


def get_daily_best():
    """ """
    CrawllerList = [Ygosu(), Ppomppu(), Theqoo(), Instiz(), Ruliweb()]
    for i in CrawllerList:
        try:
            i.get_daily_best()
        except Exception as e:
            logger.error(e)
    return JSONResponse(content={"response": "데일리 베스트 가져오기 완료"})
