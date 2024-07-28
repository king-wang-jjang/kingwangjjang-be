from utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
def format_string(email: str) -> str:
    return email.strip() \
                .replace(" ", "") \
                .replace("\n","") \
                .replace("\r","") \
                .lower()