import logging
import pymongo
# from app.utils.loghandler import catch_exception,setup_logger
# import sys
# sys.excepthook = catch_exception
from app.db.context import Database
from pymongo.errors import ConnectionFailure

logger = logging.getLogger()

class MongoController(object):
    def __init__(self):
        try:
            Database.client.admin.command('ping')
            self.db = Database
            logger.info("Successfully connected to the database")
        except ConnectionFailure as e:
            logger.error("Could not connect to the database: %s", e)

        
    def find(self, collection_name, query):
        collection = self.db.get_collection(collection_name)
        return list(collection.find(query))

    def insert_one(self, collection_name, document):
        collection = self.db.get_collection(collection_name)
        return collection.insert_one(document)

    def update_one(self, collection_name, query, update):
        collection = self.db.get_collection(collection_name)
        return collection.update_one(query, update)

    def delete_one(self, collection_name, query):
        collection = self.db.get_collection(collection_name)
        return collection.delete_one(query)

    def get_real_time_best(self, index, limit):
        collection = self.db.get_collection('RealTime')
        return list(collection.find().sort("create_time", pymongo.DESCENDING).skip(index * limit).limit(limit))

    def get_daily_best(self, index, limit):
        collection = self.db.get_collection('Daily')
        return list(collection.find().sort("create_time", pymongo.DESCENDING).skip(index + limit).limit(limit))
