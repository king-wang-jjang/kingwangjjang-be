import threading
import logging

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import settings, MongoClient

from app.db.mongo_controller import MongoController

import sys
db_controller = MongoController()

def get_likes(board_id: str, site: str):
    try:
        count_object = db_controller.find('Count', {'board_id': board_id, 'site': site})[0]
        return count_object['likes']

    except IndexError:
        count_object = db_controller.insert_one('Count',{'board_id': board_id, 'site': site, 'likes': 0, 'views': 0})
        return 0


def add_likes(board_id: str, site: str):
    try:
        count_object = db_controller.find('Count', {'board_id': board_id, 'site': site})[0]
        db_controller.update_one('Count',
                                 {'_id': count_object['_id']},
                                 {'$set': {'likes': count_object['likes'] + 1}})
        return count_object['likes'] + 1
    except IndexError:
        count_object = db_controller.insert_one('Count', {'board_id': board_id, 'site': site, 'likes': 0, 'views': 0})
        db_controller.update_one('Count',
                                 {'_id': count_object['_id']},
                                 {'$set': {'likes': count_object['likes'] + 1}})
        return 1