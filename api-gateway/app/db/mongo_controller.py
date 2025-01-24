import logging
import pymongo
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
