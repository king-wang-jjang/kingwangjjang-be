from app.db.context import create_db
from app.db.context import auto_create_db
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
# create_db()
auto_create_db()