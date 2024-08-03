from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
def add(app: FastAPI):
    app.mount("/static", StaticFiles(directory="static"), name="static")