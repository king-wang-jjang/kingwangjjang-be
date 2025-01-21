from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.loghandler import catch_exception
import sys
from starlette.middleware.sessions import SessionMiddleware

sys.excepthook = catch_exception
origins = [
    "http://localhost:8083",  
    "https://top1.kr",  
]

def add(app: FastAPI):
    app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])
    # app.add_middleware(SessionMiddleware, secret_key="some-random-string")
