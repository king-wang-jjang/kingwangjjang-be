import datetime
from typing import List
import strawberry
from fastapi import HTTPException
from bson.objectid import ObjectId

from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger
from .comment_type import Comment, CommentEntry, ReplyEntry


logger = setup_logger()
db_controller = MongoController()


@strawberry.type
class Query:
    @strawberry.field
    def comments(self, board_id: str, site: str) -> Comment:
        try:
            # board_id를 배열 형태로 변환하여 MongoDB에서 검색
            board_id_array = [board_id, int(board_id)] if board_id.isdigit() else [board_id]
            rows = db_controller.find("Comment", {"board_id": board_id_array, "site": site})
            entries: List[CommentEntry] = []
            for row in rows:
                replies = [
                    ReplyEntry(
                        board_id=rep.get("board_id", ""),
                        site=rep.get("site", ""),
                        user_id=rep.get("user_id", ""),
                        comment=rep.get("comment", ""),
                        timestamp=rep.get("timestamp"),
                    )
                    for rep in row.get("reply", [])
                ]
                entries.append(
                    CommentEntry(
                        _id=str(row.get("_id")),
                        board_id=row.get("board_id", ""),
                        site=row.get("site", ""),
                        user_id=row.get("user_id", ""),
                        comment=row.get("comment", ""),
                        reply=replies,
                        timestamp=row.get("timestamp"),
                    )
                )
            return Comment(board_id=board_id, site=site, comments=entries)
        except Exception as e:
            logger.exception(f"Error fetching comments for board_id={board_id}, site={site}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch comments")


@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_comment(self, board_id: str, site: str, user_id: str, comment: str) -> Comment:
        try:
            # board_id를 배열 형태로 변환하여 MongoDB에 저장
            board_id_array = [board_id, int(board_id)] if board_id.isdigit() else [board_id]
            doc = {
                "board_id": board_id_array,
                "site": site,
                "user_id": user_id,
                "comment": comment,
                "reply": [],
                "timestamp": datetime.datetime.now(),
            }
            db_controller.insert_one("Comment", doc)
            rows = db_controller.find("Comment", {"board_id": board_id_array, "site": site})
            entries: List[CommentEntry] = []
            for row in rows:
                entries.append(
                    CommentEntry(
                        _id=str(row.get("_id")),
                        board_id=row.get("board_id", ""),
                        site=row.get("site", ""),
                        user_id=row.get("user_id", ""),
                        comment=row.get("comment", ""),
                        reply=[
                            ReplyEntry(
                                board_id=rep.get("board_id", ""),
                                site=rep.get("site", ""),
                                user_id=rep.get("user_id", ""),
                                comment=rep.get("comment", ""),
                                timestamp=rep.get("timestamp"),
                            )
                            for rep in row.get("reply", [])
                        ],
                        timestamp=row.get("timestamp"),
                    )
                )
            return Comment(board_id=board_id, site=site, comments=entries)
        except Exception as e:
            logger.exception(f"Error adding comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to add comment")

    @strawberry.mutation
    def add_reply(self, board_id: str, site: str, user_id: str, parent_comment: str, reply: str) -> CommentEntry:
        try:
            parent = db_controller.find("Comment", {"_id": ObjectId(parent_comment)})[0]
            # board_id를 배열 형태로 변환
            board_id_array = [board_id, int(board_id)] if board_id.isdigit() else [board_id]
            reply_data = {
                "board_id": board_id_array,
                "site": site,
                "user_id": user_id,
                "comment": reply,
                "timestamp": datetime.datetime.now(),
            }
            parent["reply"].append(reply_data)
            db_controller.update_one("Comment", {"_id": ObjectId(parent_comment)}, {"$set": parent})
            updated = db_controller.find("Comment", {"_id": ObjectId(parent_comment)})[0]
            return CommentEntry(
                _id=str(updated.get("_id")),
                board_id=updated.get("board_id", ""),
                site=updated.get("site", ""),
                user_id=updated.get("user_id", ""),
                comment=updated.get("comment", ""),
                reply=[
                    ReplyEntry(
                        board_id=rep.get("board_id", ""),
                        site=rep.get("site", ""),
                        user_id=rep.get("user_id", ""),
                        comment=rep.get("comment", ""),
                        timestamp=rep.get("timestamp"),
                    )
                    for rep in updated.get("reply", [])
                ],
                timestamp=updated.get("timestamp"),
            )
        except Exception as e:
            logger.exception(f"Error adding reply: {e}")
            raise HTTPException(status_code=500, detail="Failed to add reply")


schema = strawberry.Schema(query=Query, mutation=Mutation)

