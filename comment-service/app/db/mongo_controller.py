import logging
import pymongo
from pymongo.errors import ConnectionFailure
from app.db.context import Database


logger = logging.getLogger()


class MongoController(object):
    def __init__(self):
        try:
            Database.client.admin.command('ping')
            self.db = Database
            logger.info("Successfully connected to the database (comment-service)")
        except ConnectionFailure as e:
            self.db = None
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


