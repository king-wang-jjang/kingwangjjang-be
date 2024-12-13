import datetime
import sys
import logging
from fastapi import HTTPException
from bson.objectid import ObjectId

from app.db.mongo_controller import MongoController
from app.utils.loghandler import catch_exception

# Set up exception hook and logger
sys.excepthook = catch_exception
db_controller = MongoController()

logger = logging.getLogger(__name__)


def board_comment_add(board_id: str, site: str, userid: str, comment: str):
    """
    Adds a comment to the specified board and site.

    :param board_id: ID of the board
    :param site: Site identifier
    :param userid: ID of the user posting the comment
    :param comment: Comment text
    :return: The updated comment collection
    """
    try:
        logger.info(f"Adding comment for board_id: {board_id}, site: {site}")
        comment_data = {
            "board_id": board_id,
            "site": site,
            "user_id": userid,
            "comment": comment,
            "reply": [],
            "timestamp": datetime.datetime.now(),
        }

        # Insert the comment into the database
        db_controller.insert_one("Comment", comment_data)
        logger.info(f"Comment added for board_id: {board_id}")

        # Retrieve and return all comments for the given board_id and site
        collection = db_controller.find("Comment", {"board_id": board_id, "site": site})
        return collection
    except Exception as e:
        logger.error(f"Error adding comment for board_id {board_id}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while adding the comment.")


def board_reply_add(board_id: str, site: str, userid: str, reply: str, parent_comment: str):
    """
    Adds a reply to an existing comment.

    :param board_id: ID of the board
    :param site: Site identifier
    :param userid: ID of the user posting the reply
    :param reply: Reply text
    :param parent_comment: ID of the parent comment to reply to
    :return: The updated comment with the reply
    """
    try:
        logger.info(f"Adding reply to comment {parent_comment} on board_id: {board_id}, site: {site}")
        comment_data = {
            "board_id": board_id,
            "site": site,
            "user_id": userid,
            "comment": reply,
            "timestamp": datetime.datetime.now(),
        }

        # Find the parent comment
        parent_comment_doc = db_controller.find("Comment", {"_id": ObjectId(parent_comment)})[0]

        # Add the reply to the parent comment's reply list
        parent_comment_doc["reply"].append(comment_data)

        # Update the parent comment with the new reply
        db_controller.update_one("Comment", {"_id": ObjectId(parent_comment)}, {"$set": parent_comment_doc})
        logger.info(f"Reply added to comment {parent_comment}")

        # Retrieve and return the updated parent comment
        return db_controller.find("Comment", {"_id": ObjectId(parent_comment)})
    except Exception as e:
        logger.error(f"Error adding reply to comment {parent_comment} on board_id {board_id}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while adding the reply.")
