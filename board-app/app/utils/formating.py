from app.utils.loghandler import setup_logger
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
logger = setup_logger()
def format_string(email: str) -> str:
    logger.debug(f'Formatting email: {email}')
    return email.strip() \
                .replace(" ", "") \
                .replace("\n","") \
                .replace("\r","") \
                .lower()