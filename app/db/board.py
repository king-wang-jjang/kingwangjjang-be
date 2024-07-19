from typing import Optional, Text

from pydantic import Field
from pymongo import MongoClient
from config import Config

from mongotic.model import MongoBaseModel
from mongotic.orm import Session as SessionType
from mongotic.orm import sessionmaker


class Board(MongoBaseModel):
    __databasename__ = "test_database"
    __tablename__ = "board"

    type : Text #(img | text | video)
    url : Text
    contents : Text #(video: null, img: text, text: text)



mongo_engine = MongoClient(Config.MONGO_URI)
db = mongo_engine[Board.__databasename__]
if Board.__tablename__ not in db.list_collection_names():
    db.create_collection(Board.__tablename__)

Session = sessionmaker(bind=mongo_engine)
session = Session()
