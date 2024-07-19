from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
class LLM:
    def __init__(self):

        template = """
        너는 긴 계시물을 요약해주는 AI야.
        5줄로 요약해주면 돼.
        
        글:"""
        system_message_prompt = SystemMessagePromptTemplate.from_template(template)
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        llm = ChatOllama(
            model="gemma2"
        )  # assuming you have Ollama installed and have llama3 model pulled with `ollama pull llama3 `
        self.chain = chat_prompt | llm
    def call(self,content:str):
        return self.chain.invoke({"text":content})


ai = LLM()
content = """
군, 북 오물풍선에 확성기로 재차 맞대응…10시간 가동(종합2보)

송고시간2024-07-19 11:35

지난달 9일 이후 39일 만에 재가동…살포시간 맞춰 방송 시간 5배로 늘려
북한이 또 오물풍선 살포하면 낮 시간대 가동 가능성도
대북 확성기 방송
대북 확성기 방송

(서울=연합뉴스) 대통령실은 9일 긴급 국가안전보장회의(NSC) 상임위원회의를 열어 이날 중 대북 확성기를 설치하고 방송을 실시하기로 결정했다고 밝혔다. 사진은 지난 2004년 6월 서부전선에 설치된 대북 확성기가 철거되는 모습. 2024.6.9 [연합뉴스 자료사진] jeong@yna.co.kr

(서울=연합뉴스) 김호준 기자 = 군 당국이 북한의 대남 오물풍선 살포에 대응해 18∼19일 전방 지역에서 대북 심리전 수단인 확성기 방송을 가동했다고 밝혔다.

합동참모본부는 19일 출입기자단에 배포한 문자메시지를 통해 "우리 군은 북한의 지속적인 오물풍선 살포에 대해 여러 차례 엄중히 경고한 바와 같이 어제 저녁부터 오늘 새벽까지 오물풍선을 부양한 지역에 대해 대북 확성기 방송을 실시했다"고 밝혔다.

군 당국의 대북 확성기 방송 가동은 지난달 9일 이후 39일 만이다.

북한은 전날 오후 5시께부터 이날 새벽까지 대남 오물풍선을 살포했다. 북한이 남쪽을 향해 오물풍선을 날려 보낸 것은 지난달 26일 이후 22일 만이다.
ADVERTISEMENT
ADVERTISEMENT

합참 관계자는 연합뉴스에 "북한의 대남 오물풍선 살포를 식별하고 바로 확성기 방송 가동 준비에 들어가 어제 오후 6시께부터 오늘 새벽 4∼5시까지 10시간 정도 가동했다"고 밝혔다.

지난달 9일 대북 확성기 가동 때 2시간 방송한 것에 비해 이번에는 가동 시간이 5배로 늘어난 것으로, 북한의 오물풍선 살포 시간에 맞춰서 진행됐다.

군 당국은 북한의 오물풍선을 넘어온 서부전선에 배치된 고정식 확성기의 일부를 가동한 것으로 전해졌다.

군 당국은 지난달 9일 대북 확성기 가동에도 북한의 오물풍선 살포가 계속됐지만 북한의 태도 변화를 촉구하며 대북 확성기로 다시 맞대응하지는 않았다.

그런데도 북한의 오물풍선 살포가 이어지자 지난달 27일 "북한이 종이를 넣은 쓰레기 풍선을 계속 보낸다면 우리는 확성기 방송을 재개할 수밖에 없다"고 경고했고 북한이 전날 또 오물풍선을 부양하자 이를 실행에 옮긴 것이다.

이 관계자는 올해 들어 두 번째로 대북 확성기를 가동한 이유에 대해 "우리 군의 지속적인 경고에도 북한이 대남 오물풍선을 재차 살포함에 따라 대북 경고 메시지를 발신한 것"이라고 설명했다.

군 당국이 대북 심리전 수단인 전방 지역 확성기를 재차 가동함에 따라 북한이 반발할 것으로 예상된다.

합참은 이날 입장문을 통해 "집중호우로 인해 우리 국민뿐 아니라 북한 주민에게도 심대한 피해가 발생하고 있는 상황에서 북한은 또다시 저급하고 치졸한 행위를 반복하고 있다"고 밝혔다.

그러면서 "북한 정권은 쓰레기를 살포할 여력이 있다면 경제난과 식량난으로 도탄에 빠져있는 북한 주민들을 이용만 하지 말고 먼저 살펴야 할 것"이라고 지적했다.

합참은 또한 "만약 북한이 우리 경고를 무시하고 또다시 이러한 행태를 반복한다면 우리 군은 필요한 모든 조치를 통해 반드시 응분의 대가를 치르게 할 것"이라고 경고했다.

이어 "이런 사태의 모든 책임은 전적으로 북한 정권에 있음을 분명히 밝히며, 이와 같은 비열한 방식의 행위를 즉각 중단할 것을 강력히 촉구한다"면서 "향후 우리 군의 대응은 전적으로 북한의 행동에 달려있다"고 덧붙였다.

합참 관계자는 이날 언론 브리핑에서 '앞으로 북한이 오물 풍선을 보낼 때마다 대북 방송을 실시할 계획이냐'는 질문에 "북한이 우리 군의 대응을 예측할 수 있게 해서는 곤란하다"면서 "그렇게 할 수도 있겠지만, 작전 전략을 공개할 수는 없다"고 답했다.

군 당국은 그간 전략적 유연성을 가지고 대북 확성기를 가동할 방침이라고 밝혀왔다.

지난 4월부터 북한군이 비무장지대(DMZ) 북측 지역에서 대규모 병력을 동원해 지뢰매설 등의 작업을 진행 중인 점을 고려해 낮 시간대에 대북 확성기 방송을 실시할 가능성도 있다. 지금까지 두 차례 대북 확성기 방송은 늦은 오후와 저녁, 새벽 시간대에 이뤄졌다.

이 관계자는 '북한군의 오물 풍선 부양 원점을 타격할 수도 있느냐'는 질문에는 "여러 옵션을 가지고 있다"며 즉답을 피했다.

그는 '우리 군의 대북 방송에 대응해 북한도 대남 방송을 실시했느냐'는 질문에는 "북한군 특이동향은 없다"며 "북한 대남 방송도 현재까지 식별된 바 없다"고 답했다.

hojun@yna.co.kr

제보는 카카오톡 okjebo
<저작권자(c) 연합뉴스, 무단 전재-재배포, AI 학습 및 활용 금지> 2024/07/19 11:35 송고 """
print(ai.call(content=content))