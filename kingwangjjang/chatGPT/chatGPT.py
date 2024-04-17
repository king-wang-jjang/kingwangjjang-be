import openai
from kingwangjjang.settings import CHATGPT_API_KEY # settings.py에서 API KEY를 가져옵니다.
import logging

logger = logging.getLogger("")

class ChatGPT:
    def __init__(self):
        openai.api_key = CHATGPT_API_KEY # API키 입니다. 외부에 공개하면 안됩니다.
        self.model = "gpt-3.5-turbo" # 모델 지정
        self.max_tokens = 1024       # 최대 토큰 수 제한
        self.n = 1                   # 답변 개수
        self.stop = None             # 답변 중단 예약어 설정
        self.temperature = 0.5       # 답변의 창의성 설정
        
    def get_completion(self, content): 
        user_message = {"role": "user", "content": content}
        completion = openai.ChatCompletion.create(
            model = self.model,
            messages = [user_message],
            max_tokens = self.max_tokens,
            n = self.n,
            stop = self.stop, 
            temperature = self.temperature
        )

        # gpt로부터 응답을 받습니다.
        assistance_content:str = completion.choices[0].message['content'].strip()

        # assistance에 이전 대화 답변을 저장합니다.
        # cls.messages.append({"role": "assistant", "content": f"{assistance_content}"})

        logger.info(f'ChatGPT : {assistance_content}')
        return assistance_content
