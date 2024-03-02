from django.shortcuts import render 
from django.http import JsonResponse 
from .gpt_response import ChatGptApi # gpt_response.py 파일에서 클래스를 가져옵니다.
import openai
import os
from kingwangjjang.settings import CHATGPT_API_KEY # settings.py에서 API KEY를 가져옵니다.


# chatgpt에게 질문한 내용의 답변을 받아와 index.html로 전달합니다.
def gpt_view(request): 
	if request.method == 'POST':
		prompt = request.POST.get('prompt') # 클라이언트의 질문 중 'prompt'인 부분을 받아옵니다.
		prompt=str(prompt) # 문자열로 변환 후
		response = ChatGptApi.get_completion(prompt) # gpt에게 질문합니다.
		return JsonResponse({'response': response}) # 답변을 json으로 반환합니다.
	return render(request, 'index.html') 