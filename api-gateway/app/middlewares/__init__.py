from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception

from .auth_middleware import AuthMiddleware, UserInfoMiddleware

__all__ = ["AuthMiddleware", "UserInfoMiddleware"]