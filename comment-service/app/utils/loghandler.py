import logging
import logging.handlers
from colorama import Fore, init, Style
from app.config import Config
import os 
init(autoreset=True)


def setup_logger():
    logger = logging.getLogger("comment-service")
    logger.setLevel(logging.INFO)

    log_directory = "log"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        f"{log_directory}/comment-service.log", when="midnight", interval=7, backupCount=30
    )
    file_handler.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(levelname)s: [%(asctime)s]%(name)s %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False

    return logger


def catch_exception(exc_type, exc_value, exc_traceback):
    logger = setup_logger() if Config.get_env("SERVER_RUN_MODE") == "TRUE" else logging.getLogger("")
    logger.exception("Unexpected exception.", exc_info=(exc_type, exc_value, exc_traceback))


