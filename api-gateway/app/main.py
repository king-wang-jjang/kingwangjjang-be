# from typing import Union
from app.routes import index
from fastapi import FastAPI

app = FastAPI()

app.include_router(index.router)
