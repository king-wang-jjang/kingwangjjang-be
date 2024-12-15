# from typing import Union
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

# from app.routes import index
from fastapi import FastAPI

app = FastAPI()

# app.include_router(index.router)
