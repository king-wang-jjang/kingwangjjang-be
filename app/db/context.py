from pymongo import MongoClient
from config import Config


class Database:
    client = MongoClient(Config.MONGO_URI)
    db = client.get_default_database()

    @staticmethod
    def get_collection(name):
        return Database.db[name]