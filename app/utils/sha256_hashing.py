from time import time
from hashlib import sha256
from random import randint

from constants import HASH_SALT
from utils.loghandler import catch_exception,setup_logger
import sys
logger = setup_logger()
sys.excepthook = catch_exception

class HashLib:
    @staticmethod
    def hash(password: str) -> str:
        to_hash = password + HASH_SALT
        logger.debug(f"Hashing {to_hash}")
        return sha256(to_hash.encode()).hexdigest()

    @staticmethod
    def validate(plain_password: str, hashed_password: str) -> bool:
        logger.debug(f"Validating {plain_password}")
        return hash(plain_password) == hashed_password

    @staticmethod
    def random_hash() -> str:
        random_number = randint(0, 999999)
        logger.debug(f"Random number {random_number}")
        timestamp = time()
        to_hash = f"{timestamp} {random_number} {HASH_SALT}"
        logger.debug(f"Random Hashing {to_hash}")
        return sha256(to_hash.encode()).hexdigest()