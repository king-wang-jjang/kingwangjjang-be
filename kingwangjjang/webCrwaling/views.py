import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from chatGPT.chatGPT import ChatGPT
from constants import DEFAILT_GPT_ANSWER

from .communityWebsite.models import RealTime
from django.views.decorators.csrf import csrf_exempt
from webCrwaling.communityWebsite.dcinside import Dcinside 

### 이미지가 많은 상황
# JPG -> Text 
# 댓글을 요약 ( 추천 수가 몇 개이상 )
@csrf_exempt
def board_summary(board_id):
    realtime_object = get_object_or_404(RealTime, _id=board_id)
     
    if (realtime_object.GPTAnswer != DEFAILT_GPT_ANSWER):
        return realtime_object.GPTAnswer
        return True # 이미 요약이 완료된 상태
        
    dcincideCrwaller = Dcinside()
    json_contents = dcincideCrwaller.get_board_contents(board_id)
    str_contents = ''
    for a in json_contents:
        if 'content' in a:
            str_contents += a['content']
    
    # GPT 요약
    prompt= "아래 내용에서 이상한 문자는 제외하고 5줄로 요약해줘" + str_contents
    chatGPT = ChatGPT()
    print("URL: https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id)
    response = chatGPT.get_completion(content=prompt)

    # Insert Mongodb
    realtime_object.GPTAnswer = response
    realtime_object.save()
    
    return response

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
    
def get_real_time_best(request):
    if request.method == 'get':
        dcincideCrwaller = Dcinside()
        dcincideCrwaller.get_real_time_best()

        return JsonResponse({'response': "성공하는 루트 추가해야함"}) 
