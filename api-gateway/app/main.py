# from typing import Union
import sys
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.routes import index
from app.routes.auth import auth_controllers
from fastapi import FastAPI

app = FastAPI()
origins = [
    "http://localhost:8083",  
    "https://xn--hz2b47s.kr",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_controllers.router)
app.include_router(index.router)

