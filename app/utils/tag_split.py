from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
from config import Config
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception

# 자료구조 정의 (pydantic)
class Parser_model(BaseModel):
    tags: list = Field(description="글들에 태그들")
class Tagsplit:
    def __init__(self):

        template = """
        너는 게시물 태그 분석 전문가야.
        너는 []사이에 글들을 읽어서 태그로 나눠야돼. 예를들어 정치,IT,연애 이런식으로
        또한 너는 리턴해줄때 json포맷으로 리턴해줘야해.
        ["연애","유머"] 이런식으로
        분석할 내용:"""
        output_parser = JsonOutputParser(pydantic_object=Parser_model)

        format_instructions = output_parser.get_format_instructions()
        system_message_prompt = SystemMessagePromptTemplate.from_template(template)
        human_template = "[{text}]"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        llm = ChatOpenAI(
            model="gpt-4o",
            openai_api_key=Config().get_env("CHATGPT_API_KEY")
        )  # assuming you have Ollama installed and have llama3 model pulled with `ollama pull llama3 `
        self.chain = chat_prompt | llm | output_parser
    def call(self,content:str):
        return self.chain.invoke({"text":content})
        # return "일시적인 오류가 발생함."

