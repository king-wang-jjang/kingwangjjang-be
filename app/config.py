import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    USERNAME = quote_plus(os.getenv("MONGO_USERNAME"))
    PASSWORD = quote_plus(os.getenv("MONGO_PASSWORD"))
    HOST = os.getenv("MONGO_HOST")
    DATABASE = os.getenv("MONGO_DATABASE")

    MONGO_URI = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:27017/{DATABASE}"
