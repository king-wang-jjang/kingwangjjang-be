# from typing import Union
import sys
sys.path.append("/app") #내부 모듈이 임포트 되기전에 가장 먼저 임포트 되야함.

from app.routes import index
from fastapi import FastAPI

app = FastAPI()

app.include_router(index.router)
