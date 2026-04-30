import builtins
import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")


class AppStartupTests(unittest.TestCase):
    def test_app_imports_without_strawberry(self):
        real_import = builtins.__import__

        def block_strawberry(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "strawberry" or name.startswith("strawberry."):
                raise ModuleNotFoundError("No module named 'strawberry'")
            return real_import(name, globals, locals, fromlist, level)

        fake_users_module = types.ModuleType("app.repositories.users")
        fake_users_module.UserRepository = object

        with (
            patch.dict(sys.modules, {"app.repositories.users": fake_users_module}),
            patch.object(builtins, "__import__", block_strawberry),
        ):
            for module_name in list(sys.modules):
                if (
                    module_name == "app.main"
                    or module_name.startswith("app.graphql")
                    or module_name == "strawberry"
                    or module_name.startswith("strawberry.")
                ):
                    sys.modules.pop(module_name, None)

            main = importlib.import_module("app.main")

        self.assertNotIn("/user-graphql", {route.path for route in main.app.routes})


if __name__ == "__main__":
    unittest.main()
