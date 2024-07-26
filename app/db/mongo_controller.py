import logging
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
import pymongo
logger = logging.getLogger("")
from db.context import Database
from config import Config

class MongoController(object):
    def __init__(self):
        self.db = Database

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
