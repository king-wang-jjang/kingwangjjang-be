import json
import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from chatGPT.chatGPT import ChatGPT
from mongo import DBController

from app.webCrwaling.communityWebsite.ygosu import Ygosu
from app.webCrwaling.communityWebsite.dcinside import Dcinside

from constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE, SITE_YGOSU

logger = logging.getLogger("")

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요한 도메인으로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

board_semaphores = {}
db_controller = DBController()

router = APIRouter()


@router.post("/board_summary/")
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
        realtime_object = db_controller.select('RealTime', {'board_id': board_id, 'site': site})[0]
        GPT_Object_id = realtime_object['GPTAnswer']
        GPT_object = db_controller.select('GPT', {'_id': GPT_Object_id})[0]

        if GPT_object['answer'] != DEFAULT_GPT_ANSWER:
            return GPT_object['answer']

        if site == SITE_DCINSIDE:
            crawler_instance = Dcinside()
        elif site == SITE_YGOSU:
            crawler_instance = Ygosu()
        elif site == SITE_PPOMPPU:
            crawler_instance = Ppomppu()
        json_contents = crawler_instance.get_board_contents(board_id)

        str_contents = ''
        for content in json_contents:
            if 'content' in content:
                str_contents += content['content']
        response = str_contents

        # GPT 요약
        prompt = f"너는 게시물 분석 및 요약 전문가야. 아래의 []에 들어가는 내용을 분석해서 정확하고 명확하게 정리하는데에 특별한 전문성이 있고, 컨텐츠를 요약할 때는 'TextRank' 알고리즘을 사용하는게 능숙해. 이제 아래 []로 감싸진 내용을 너가 읽을 수 있는 단어들만 읽어서 게시글의 전체 내용을 1000자 이내로 요약해. 만약 []의 내용이 아무런 값이 없는 공백이라면, 너는 '게시물의 내용을 읽을 수 없습니다.' 라는 대답만 하면 돼. 분석할 내용: [{str_contents}]"
        chatGPT = ChatGPT()
        logger.info("URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id)
        response = chatGPT.get_completion(content=prompt)

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


@router.post("/board_summary_rest/")
async def board_summary_rest(request: Request):
    if request.method == 'POST':
        data = await request.json()
        board_id = data.get('board_id')
        site = data.get('site')

        return await board_summary(board_id, site)
    else:
        dcincideCrwaller = Dcinside()
        dcincideCrwaller.get_real_time_best()

        return JSONResponse(content={'response': "성공하는 루트 추가해야함"})


@router.get("/get_real_time_best/")
async def get_real_time_best():
    dcincideCrwaller = Dcinside()
    ygosuCrawller = Ygosu()
    # dcincideCrwaller.get_real_time_best()
    ygosuCrawller.get_real_time_best()
    return JSONResponse(content={'response': "실시간 베스트 가져오기 완료"})


@router.get("/get_daily_best/")
async def get_daily_best():
    ygosuCrawller = Ygosu()
    ygosuCrawller.get_daily_best()
    return JSONResponse(content={'response': "데일리 베스트 가져오기 완료"})


# 간단한 a + b 함수
@router.get("/add/")
async def add(a: int, b: int):
    return JSONResponse(content={'result': a + b})


app.include_router(router)
