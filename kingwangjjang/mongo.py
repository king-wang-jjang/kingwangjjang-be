import logging
from urllib.parse import quote_plus
from django.conf import settings
import pymongo
logger = logging.getLogger("")
class DBController(object):

    def __init__(self):
        self.db_host = getattr(settings, 'DB_HOST', 'localhost')
        self.db_name = getattr(settings, 'DB_NAME', None)
        self.db_user = getattr(settings, 'DB_USER', None)
        self.db_password = getattr(settings, 'DB_PASSWORD', None)
        escaped_user = quote_plus(self.db_user)
        escaped_password = quote_plus(self.db_password)
        self.dbUri = f'mongodb://{escaped_user}:{escaped_password}@{self.db_host}/{self.db_name}?authMechanism=SCRAM-SHA-256'

    def GetDBHandle(self):
        client = pymongo.MongoClient(self.dbUri)
        dbHandle = client.get_default_database()  # 기본 데이터베이스 가져오기
        return dbHandle, client
    
    def insert(self, collection_name, data):
        dbHandle, client = self.GetDBHandle()
        collection = dbHandle[collection_name]
        result = collection.insert_one(data)
        logging.info(f"{collection_name}, Data: {data}")
        client.close()
        return result

    def select(self, collection_name, query=None):
        dbHandle, client = self.GetDBHandle()
        collection = dbHandle[collection_name]

        if query:
            logging.debug(f"Query: {query}")
            result = collection.find(query)
            
        else:
            result = collection.find()

        result_list = list(result)

        client.close()
        return result_list

    def get_collection(self, collection_name):
        dbHandle, client = self.GetDBHandle()
        collection = dbHandle[collection_name]
        return collection
        
    def update_one(self, collection_name, filter, update):
        dbHandle, client = self.GetDBHandle()
        collection = dbHandle[collection_name]

        # update_one() 메서드를 사용하여 단일 문서를 업데이트합니다.
        result = collection.update_one(filter, update)

        # 업데이트 결과를 반환합니다.
        client.close()
        return result
