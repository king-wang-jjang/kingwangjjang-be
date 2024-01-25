from pymongo import MongoClient
from django.conf import settings
import pymongo

class DBController(object):

    def __init__(self):
        self.host = getattr(settings, 'DB_HOST', None)
        self.userName = getattr(settings, 'DB_USER', None)
        self.passWord = getattr(settings, 'DB_PASSWORD', None)
        self.dbName = getattr(settings, 'DB_NAME', None)
        self.dbUri = getattr(settings, 'DB_URI', None)

    def GetDBHandle(self):
        client = pymongo.MongoClient(self.dbUri)
        dbHandle = client[self.dbName]

        return dbHandle, client
    
    def insert(self, collection_name, data):
        dbHandle, client = self.GetDBHandle()
        collection = dbHandle[collection_name]
        result = collection.insert_one(data)
        client.close()
        return result
