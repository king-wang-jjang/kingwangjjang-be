import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from utils import lifespan
from routes.auth import auth_controller
from routes.page import page_controller
from routes.user import user_controller

from middlewares import cors_middleware
# from middlewares import static_middleware

app = FastAPI(lifespan=lifespan.lifespan)

cors_middleware.add(app)
# static_middleware.add(app)

app.include_router(auth_controller.router)
app.include_router(page_controller.router)
app.include_router(user_controller.router)