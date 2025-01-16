from datetime import datetime

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from app.db.context import Database
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception

router = APIRouter(
    prefix="",
    tags=["Pages"],
    default_response_class=HTMLResponse
)

@router.get("/")
def main(req: Request):
    now = datetime.now()
    collection = Database.client.list_database_names()
    print(f"Databases: {collection}")
    return "collection"
