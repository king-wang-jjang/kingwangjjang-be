import os
from dotenv import load_dotenv,find_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    USERNAME = quote_plus(os.getenv("DB_USER"))
    PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))
    HOST = os.getenv("DB_HOST")
    DATABASE = os.getenv("DB_NAME")

    MONGO_URI = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:27017/{DATABASE}"
