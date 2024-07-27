import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings

from db.mongo_controller import MongoController
from services.web_crwaling.community_website.ppomppu import Ppomppu
from services.web_crwaling.community_website.theqoo import Theqoo
from services.web_crwaling.community_website.ygosu import Ygosu

from utils.llm import LLM
from constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE, SITE_YGOSU,SITE_PPOMPPU,SITE_THEQOO
from utils.loghandler import setup_logger

logger = setup_logger()

app = FastAPI()

board_semaphores = {}
db_controller = MongoController()

router = APIRouter()


async def board_summary(board_id: str, site: str):
    global board_semaphores
    semaphore_label = site + board_id

    if board_id not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)
    if not acquired:
        raise HTTPException(status_code=429, detail='요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.')

    try:
        realtime_object = db_controller.find('RealTime', {'board_id': board_id, 'site': site})[0]
        GPT_Object_id = realtime_object['GPTAnswer']
        GPT_object = db_controller.find('GPT', {'_id': GPT_Object_id})[0]

        if GPT_object['answer'] != DEFAULT_GPT_ANSWER:
            return GPT_object['answer']

        # if site == SITE_DCINSIDE:
        #     crawler_instance = Dcinside()
        elif site == SITE_YGOSU:
            crawler_instance = Ygosu()
        elif site == SITE_PPOMPPU:
            crawler_instance = Ppomppu()
        elif site == SITE_THEQOO:
            crawler_instance = Theqoo()
        json_contents = crawler_instance.get_board_contents(board_id)

        str_contents = ''
        for content in json_contents:
            if 'content' in content:
                str_contents += content['content']
        response = str_contents

        # GPT 요약
        chatGPT = LLM()
        logger.info("URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id)
        response = chatGPT.call(content=str_contents)

        # Update answer
        if GPT_object:
            db_controller.update_one('GPT',
                                     {'_id': GPT_Object_id},
                                     {'$set': {'answer': response}})
            logger.info(f"{GPT_Object_id} site: {site} board_id: {board_id}문서 업데이트 완료")
        else:
            logger.error(f"{GPT_Object_id} site: {site} board_id: {board_id}해당 ObjectId로 문서를 찾을 수 없습니다.")
            return JSONResponse(content={"detail": "해당 ObjectId로 문서를 찾을 수 없습니다."}, status_code=404)

        return response
    finally:
        semaphore.release()


async def board_summary_rest(request: Request):
    if request.method == 'POST':
        data = await request.json()
        board_id = data.get('board_id')
        site = data.get('site')

        return await board_summary(board_id, site)
    # else:
    #     dcincideCrwaller = Dcinside()
    #     dcincideCrwaller.get_real_time_best()

        return JSONResponse(content={'response': "성공하는 루트 추가해야함"})


async def get_real_time_best():
    ygosuCrawller = Ygosu()
    ppomppuCrawller = Ppomppu()
    theqooCrawller = Theqoo()
    ygosuCrawller.get_real_time_best()
    theqooCrawller.get_real_time_best()
    return JSONResponse(content={'response': "실시간 베스트 가져오기 완료"})


async def get_daily_best():
    ygosuCrawller = Ygosu()
    ppomppuCrawller = Ppomppu()
    ygosuCrawller.get_daily_best()
    return JSONResponse(content={'response': "데일리 베스트 가져오기 완료"})

