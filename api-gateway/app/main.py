from typing import Union
from routes import index
from fastapi import FastAPI

app = FastAPI()

app.include_router(index.router)