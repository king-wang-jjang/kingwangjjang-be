from django.shortcuts import render 
from django.http import JsonResponse 
from .api_response import get_completion
import openai
import os
from kingwangjjang.settings import CHATGPT_API_KEY


openai.api_key =  CHATGPT_API_KEY #앞서 자신이 부여받은 API key를 넣으면 된다. 절대 외부에 공개해서는 안된다.

# chatgpt에게 질문한 내용의 답변을 받아와 index.html로 전달합니다.
def query_view(request): 
	if request.method == 'POST':
		prompt = request.POST.get('prompt') # 클라이언트의 질문 중 'prompt'인 부분을 받아옵니다.
		prompt=str(prompt) # 문자열로 변환 후
		response = get_completion(prompt) # gpt에게 질문합니다.
		return JsonResponse({'response': response}) # 답변을 json으로 반환합니다.
	return render(request, 'index.html') 