import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from app.utils.loghandler import catch_exception, setup_logger
from app.db.mongo_controller import MongoController
from bson.objectid import ObjectId
import datetime


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sys.excepthook = catch_exception
logger = setup_logger()
db_controller = MongoController()


class CommentCreate(BaseModel):
    board_id: str
    site: str
    user_id: str
    comment: str


class ReplyCreate(BaseModel):
    board_id: str
    site: str
    user_id: str
    parent_comment: str
    reply: str


@app.get("/comment")
def get_comments(board_id: str, site: str):
    try:
        collection = db_controller.find("Comment", {"board_id": board_id, "site": site})
        return collection
    except Exception as e:
        logger.exception(f"Error fetching comments for board_id={board_id}, site={site}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")


@app.post("/comment")
def add_comment(payload: CommentCreate):
    try:
        comment_data = {
            "board_id": payload.board_id,
            "site": payload.site,
            "user_id": payload.user_id,
            "comment": payload.comment,
            "reply": [],
            "timestamp": datetime.datetime.now(),
        }
        db_controller.insert_one("Comment", comment_data)
        collection = db_controller.find("Comment", {"board_id": payload.board_id, "site": payload.site})
        return collection
    except Exception as e:
        logger.exception(f"Error adding comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to add comment")


@app.post("/reply")
def add_reply(payload: ReplyCreate):
    try:
        parent = db_controller.find("Comment", {"_id": ObjectId(payload.parent_comment)})[0]
        reply_data = {
            "board_id": payload.board_id,
            "site": payload.site,
            "user_id": payload.user_id,
            "comment": payload.reply,
            "timestamp": datetime.datetime.now(),
        }
        parent["reply"].append(reply_data)
        db_controller.update_one("Comment", {"_id": ObjectId(payload.parent_comment)}, {"$set": parent})
        updated = db_controller.find("Comment", {"_id": ObjectId(payload.parent_comment)})
        return updated
    except Exception as e:
        logger.exception(f"Error adding reply: {e}")
        raise HTTPException(status_code=500, detail="Failed to add reply")


if __name__ == "__main__":
    logger.info("Starting uvicorn server (comment-service)")
    uvicorn.run("app.main:app", host="0.0.0.0", port=33335, reload=True)


