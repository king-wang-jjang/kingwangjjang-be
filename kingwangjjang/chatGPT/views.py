from django.shortcuts import render 
from django.http import JsonResponse 
import openai
import os

openai.api_key='' #앞서 자신이 부여받은 API key를 넣으면 된다. 절대 외부에 공개해서는 안된다.

messages = []

def get_completion(content): 
	# 사용자 입력을 받습니다.
	# content = input("input content: ")
	print("input message: ", content)

	# 사용자 입력을 messages에 추가해줍니다.
	messages.append({"role": "user", "content": f"{content}"})

	completion = openai.ChatCompletion.create(
		model="gpt-3.5-turbo",	# 모델 지정
		messages=messages,		# 질문 및 답변
		max_tokens=1024,		# 최대 토큰 수 제한
		n=1, 					# 답변 개수
		stop=None, 				# 답변 중단 예약어 설정
		temperature=0.5			# 답변의 창의성 설정
	)

	# gpt로부터 응답을 받습니다.
	# strip() : 응답이 올 때, 빈 공간 제거
	assistance_content = completion.choices[0].message['content'].strip()

	# assistance에 이전 대화 답변을 저장합니다.
	messages.append({"role": "assistant", "content": f"{assistance_content}"})

	print(f'ChatGPT : {assistance_content}')
	return assistance_content

def query_view(request): 
	if request.method == 'POST':
		prompt = request.POST.get('prompt') 
		prompt=str(prompt)
		response = get_completion(prompt)
		return JsonResponse({'response': response}) 
	return render(request, 'index.html') 