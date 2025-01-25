import logging
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

    def users_collection(self):
        return self.db.get_collection('users')
    
    def insert_user(self, query):
        collection = self.db.get_collection('users')
        collection.insert_one(query)
        return True

    def find_user(self, query):
        collection = self.db.get_collection('users')
        return bool(collection.find_one(query))