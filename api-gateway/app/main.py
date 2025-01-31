# from typing import Union
import sys
from pathlib import Path

import strawberry
from app.graphql.schema import Query, schema

from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.routes import index
from app.routes.auth import auth_controllers
from fastapi import FastAPI

app = FastAPI()
origins = [
    "http://localhost:8083",  
    "https://top1.kr",
    "https://마약.kr",
    "http://localhost:33330",
]
app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql") 
app.include_router(auth_controllers.router)
app.include_router(index.router)

