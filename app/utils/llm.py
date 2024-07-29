from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
from config import Config
import ollama
os.environ["OLLAMA_HOST"] = Config.get_env("OLLAMA_HOST")
class LLM:
    def __init__(self):

        template = """
        너는 게시물 분석 및 요약 전문가야.
        아래의 []에 들어가는 내용을 분석해서 정확하고 명확하게 정리하는데에 특별한 전문성이 있고, 컨텐츠를 요약할 때는 'TextRank' 알고리즘을 사용하는게 능숙해.
        이제 아래 []로 감싸진 내용을 너가 읽을 수 있는 단어들만 읽어서 게시글의 전체 내용을 1000자 이내로 요약해.
        만약 []의 내용이 아무런 값이 없는 공백이라면, 너는 '게시물의 내용을 읽을 수 없습니다.' 라는 대답만 하면 돼.
        분석할 내용:"""
        system_message_prompt = SystemMessagePromptTemplate.from_template(template)
        human_template = "[{text}]"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        llm = OllamaLLM(
            model="gemma2",
            base_url = Config.get_env("OLLAMA_HOST"),
            # openai_api_key=Config().get_env("CHATGPT_API_KEY"),
        )  # assuming you have Ollama installed and have llama3 model pulled with `ollama pull llama3 `
        self.chain = chat_prompt | llm
    def call(self,content:str):
        return self.chain.invoke({"text":content}).content
        # return "일시적인 오류가 발생함."
print(LLM().call("ㅌ태스트"))

