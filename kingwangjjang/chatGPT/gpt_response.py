import openai
from kingwangjjang.settings import CHATGPT_API_KEY # settings.py에서 API KEY를 가져옵니다.

messages = []

class ChatGptApi:
    openai.api_key = CHATGPT_API_KEY # API키 입니다. 외부에 공개하면 안됩니다.

    def __init__(self):
        self.model = "gpt-3.5-turbo" # 모델 지정
        self.max_tokens = 1024       # 최대 토큰 수 제한
        self.n = 1                   # 답변 개수
        self.stop = None             # 답변 중단 예약어 설정
        self.temperature = 0.5       # 답변의 창의성 설정
        
        self.completion = openai.ChatCompletion.create(
            model = self.model,
            messages = messages,		# 질문 및 답변
            max_tokens = self.max_tokens,
            n = self.n,
            stop = self.stop, 
            temperature = self.temperature
        )

    @classmethod
    def get_completion(cls, content): 
        # 사용자 입력을 받습니다.
        print("input message: ", content)

        # 사용자 입력을 messages에 추가해줍니다.
        messages.append({"role": "user", "content": f"{content}"})

        completion = cls().completion

        # gpt로부터 응답을 받습니다.
        assistance_content = completion.choices[0].message['content'].strip()

        # assistance에 이전 대화 답변을 저장합니다.
        messages.append({"role": "assistant", "content": f"{assistance_content}"})

        print(f'ChatGPT : {assistance_content}')
        return assistance_content
