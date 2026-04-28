import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.routes.comments import router as comments_router
from app.utils.loghandler import catch_exception, setup_logger

sys.excepthook = catch_exception
logger = setup_logger()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.graphql.modules.comment.comment_schema import schema as comment_schema

app.include_router(comments_router)

graphql_app = GraphQLRouter(comment_schema)
app.include_router(graphql_app, prefix="/comment-graphql")


if __name__ == "__main__":
    logger.info("Starting uvicorn server (comment-service)")
    uvicorn.run("app.main:app", host="0.0.0.0", port=33335, reload=True)


