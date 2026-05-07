from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_routes_all_local_browser_api_calls_to_local_gateway():
    http_client = (ROOT / "kingwangjjang-fe/src/api/http.ts").read_text(encoding="utf-8")

    assert "LOCAL_AUTH_PREFIXES" not in http_client
    assert "if (isLocalBrowserHost())" in http_client
    assert "return CONFIG.localServerUrl" in http_client
