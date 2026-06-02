import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from starlette.datastructures import URL


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")

from app.routes import auth


class FakeRequest:
    def __init__(self, url: str):
        self.url = URL(url)


class AuthRouteTests(unittest.TestCase):
    def test_login_uses_local_request_host_for_kakao_redirect_uri(self):
        with patch.dict(
            os.environ,
            {
                "SERVER_RUN_MODE": "FALSE",
                "KAKAO_CLIENT_ID": "kakao-client",
                "REDIRECT_URI": "http://localhost:33330/callback",
            },
            clear=False,
        ):
            response = auth.login(FakeRequest("http://192.168.0.10:33330/login"))

        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        params = parse_qs(urlparse(location).query)
        self.assertEqual(params["redirect_uri"], ["http://192.168.0.10:33330/callback"])

    def test_callback_redirect_uri_uses_env_value_outside_local_dev(self):
        with patch.dict(
            os.environ,
            {
                "SERVER_RUN_MODE": "TRUE",
                "REDIRECT_URI": "https://api.example.com/callback",
            },
            clear=False,
        ):
            redirect_uri = auth._callback_redirect_uri(
                FakeRequest("http://192.168.0.10:33330/callback")
            )

        self.assertEqual(redirect_uri, "https://api.example.com/callback")


if __name__ == "__main__":
    unittest.main()
