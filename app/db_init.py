from db.context import create_db
from db.context import auto_create_db
from utils.loghandler import catch_exception
sys.excepthook = catch_exception
# create_db()
auto_create_db()