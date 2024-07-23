from datetime import datetime
from pymongo.collection import Collection
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
import mongo

db_controller = app.mongo.DBController()

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

class RealTimeDTO(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    board_id: str
    site: str
    title: str
    url: str
    create_time: datetime
    GPTAnswer: str = "GPT 생성 중입니다. 이미지가 많은 경우 오래 걸립니다."

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @staticmethod
    def from_mongo(data):
        if data:
            return RealTimeDTO(**data)
        return None

    @staticmethod
    def find(query):
        results = db_controller.find('realtimebest', query)
        return [RealTimeDTO.from_mongo(doc) for doc in results]

    @staticmethod
    def insert(data):
        result = db_controller.insert_one('realtimebest', data.dict(by_alias=True))
        return str(result.inserted_id)

    @staticmethod
    def update(query, update):
        result = db_controller.update_one('realtimebest', query, {'$set': update})
        return result.modified_count

    @staticmethod
    def delete(query):
        result = db_controller.delete_one('realtimebest', query)
        return result.deleted_count

class DailyDTO(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    board_id: str
    site: str
    rank: int
    title: str
    url: str
    create_time: datetime
    GPTAnswer: str = "GPT 생성 중입니다. 이미지가 많은 경우 오래 걸립니다."

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @staticmethod
    def from_mongo(data):
        if data:
            return DailyDTO(**data)
        return None

    @staticmethod
    def find(query):
        results = db_controller.find('dailybest', query)
        return [DailyDTO.from_mongo(doc) for doc in results]

    @staticmethod
    def insert(data):
        result = db_controller.insert_one('dailybest', data.dict(by_alias=True))
        return str(result.inserted_id)

    @staticmethod
    def update(query, update):
        result = db_controller.update_one('dailybest', query, {'$set': update})
        return result.modified_count

    @staticmethod
    def delete(query):
        result = db_controller.delete_one('dailybest', query)
        return result.deleted_count
