import datetime
import sys

from bson.objectid import ObjectId
from fastapi import HTTPException

from app.db.mongo_controller import MongoController
from app.utils.loghandler import catch_exception

sys.excepthook = catch_exception
db_controller = MongoController()


def board_comment_add(board_id, site, userid, comment):
    """

    :param board_id: param site:
    :param userid: param comment:
    :param site:
    :param comment:

    """
    try:
        comment_data = {
            "board_id": board_id,
            "site": site,
            "user_id": userid,
            "comment": comment,
            "reply": list(),
            "timestamp": datetime.datetime.now(),
        }
        collection = db_controller.find("Comment", {
            "board_id": board_id,
            "site": site
        })
        db_controller.insert_one("Comment", comment_data)
        return collection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def board_reply_add(board_id, site, userid, reply, parrent_comment):
    """

    :param board_id: param site:
    :param userid: param reply:
    :param parrent_comment:
    :param site:
    :param reply:

    """
    try:
        comment_data = {
            "board_id": board_id,
            "site": site,
            "user_id": userid,
            "comment": reply,
            "timestamp": datetime.datetime.now(),
        }
        replys = db_controller.find("Comment",
                                    {"_id": ObjectId(parrent_comment)})[0]
        replys["reply"].append(comment_data)
        db_controller.update_one("Comment", {"_id": ObjectId(parrent_comment)},
                                 {"$set": replys})
        return db_controller.find("Comment",
                                  {"_id": ObjectId(parrent_comment)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
