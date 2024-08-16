from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception

# function for enabling CORS on web server
def add(app: FastAPI):
    app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])