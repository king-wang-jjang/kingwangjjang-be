from pymongo import MongoClient
from app.config import Config
from urllib.parse import quote_plus


class Database:
    db_host = Config().get("DB_HOST")
    db_name = Config().get("DB_NAME")
    db_user = Config().get("DB_USER")
    db_password = Config().get("DB_PASSWORD")
    escaped_user = quote_plus(db_user)
    escaped_password = quote_plus(db_password)

    client = MongoClient(f'mongodb://{escaped_user}:{escaped_password}@{db_host}/{db_name}?authMechanism=SCRAM-SHA-256')
    db = client.get_default_database()

    @staticmethod
    def get_collection(name):
        return Database.db[name]