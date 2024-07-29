from datetime import datetime
from pymongo.collection import Collection
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
from constants import DEFAULT_GPT_ANSWER
from db.mongo_controller import MongoController
from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
db_controller = MongoController()
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid object ID")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class ViwesDTO(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    board_id: str
    site: str
    views : int
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @staticmethod
    def from_mongo(data):
        if data:
            return ViwesDTO(**data)
        return None

    @staticmethod
    def find(query):
        results = db_controller.find('Count', query)
        return [ViwesDTO.from_mongo(doc) for doc in results]

    @staticmethod
    def insert(data):
        result = db_controller.insert_one('Count', data.dict(by_alias=True))
        return str(result.inserted_id)

    @staticmethod
    def update(query, update):
        result = db_controller.update_one('Count', query, {'$set': update})
        return result.modified_count

    @staticmethod
    def delete(query):
        result = db_controller.delete_one('Count', query)
        return result.deleted_count

class LikesDTO(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    board_id: str
    site: str
    likes : int
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @staticmethod
    def from_mongo(data):
        if data:
            return ViwesDTO(**data)
        return None

    @staticmethod
    def find(query):
        results = db_controller.find('Count', query)
        return [ViwesDTO.from_mongo(doc) for doc in results]

    @staticmethod
    def insert(data):
        result = db_controller.insert_one('Count', data.dict(by_alias=True))
        return str(result.inserted_id)

    @staticmethod
    def update(query, update):
        result = db_controller.update_one('Count', query, {'$set': update})
        return result.modified_count

    @staticmethod
    def delete(query):
        result = db_controller.delete_one('Count', query)
        return result.deleted_count

