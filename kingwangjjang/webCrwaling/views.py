import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import threading

from chatGPT.chatGPT import ChatGPT
from webCrwaling.communityWebsite.ygosu import Ygosu
from constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE, SITE_YGOSU

from .communityWebsite.models import RealTime
from django.views.decorators.csrf import csrf_exempt
from webCrwaling.communityWebsite.dcinside import Dcinside 
import logging

logger = logging.getLogger("")
board_semaphores = {}

@csrf_exempt
def board_summary(board_id, site):
    global board_semaphores
    semaphore_label = site + board_id

    if board_id not in board_semaphores:
        board_semaphores[semaphore_label] = threading.Semaphore(1)

    semaphore = board_semaphores[semaphore_label]
    acquired = semaphore.acquire(timeout=1)
    if not acquired:
        return '요청을 이미 처리하고 있습니다. 잠시 후 다시 선택해주세요.'

    try:
        realtime_object = get_object_or_404(RealTime, site=site, board_id=board_id)
        if realtime_object.GPTAnswer != DEFAULT_GPT_ANSWER: # 이미 요약이 완료된 상태
            return realtime_object.GPTAnswer
        
        if (site == SITE_DCINSIDE):
            crawler_instance = Dcinside()
        elif (site == SITE_YGOSU):
            crawler_instance = Ygosu()
        json_contents = crawler_instance.get_board_contents(board_id)
        str_contents = ''
        for content in json_contents:
            if 'content' in content:
                str_contents += content['content']

        # # GPT 요약
        # prompt= "아래 내용에서 이상한 문자는 제외하고 5줄로 요약해줘" + str_contents
        # chatGPT = ChatGPT()
        # logger.info("URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id)
        # response = chatGPT.get_completion(content=prompt)

        # Mongodb에 삽입
        # realtime_object.GPTAnswer = response
        realtime_object.GPTAnswer = str_contents
        realtime_object.save()
        
        return str_contents
    finally:
        semaphore.release()

@csrf_exempt
def board_summary_rest(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        board_id = data.get('board_id')

        return board_summary(board_id)
    else:
        dcincideCrwaller = Dcinside()
        dcincideCrwaller.get_real_time_best()

        return JsonResponse({'response': "성공하는 루트 추가해야함"}) 
    
def get_real_time_best():
    dcincideCrwaller = Dcinside()
    ygosuCrawller = Ygosu()
    dcincideCrwaller.get_real_time_best()
    ygosuCrawller.get_real_time_best()

def get_daily_best():
    ygosuCrawller = Ygosu()
    ygosuCrawller.get_daily_best()