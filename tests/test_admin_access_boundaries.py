import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_admin_access_module():
    path = ROOT / "api-gateway" / "app" / "services" / "admin_access.py"
    spec = importlib.util.spec_from_file_location("gateway_admin_access", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_admin_allowlist_fails_closed_and_ignores_blank_entries():
    admin_access = load_admin_access_module()

    assert admin_access.resolve_user_role("123", "") == "user"
    assert admin_access.resolve_user_role("123", " , 456, ") == "user"
    assert admin_access.resolve_user_role("456", " , 456, ") == "admin"
    assert admin_access.resolve_user_role(None, "456") == "user"


def test_gateway_owns_and_forwards_trusted_admin_role_header():
    middleware = read(ROOT / "api-gateway" / "app" / "middlewares" / "auth_middleware.py")
    proxy = read(ROOT / "api-gateway" / "app" / "routes" / "index.py")

    assert "resolve_user_role(user_id)" in middleware
    assert '"X-User-Role"' in proxy
    assert "headers.pop(header_name.lower(), None)" in proxy
    assert 'headers["X-User-Role"]' in proxy


def test_gateway_protects_ai_management_and_injects_internal_admin_token():
    proxy = read(ROOT / "api-gateway" / "app" / "routes" / "index.py")

    assert '"gptservice/api/ai/nodes"' in proxy
    assert '"gptservice/api/ai/resources"' in proxy
    assert 'getattr(request.state, "user_role", "user") != "admin"' in proxy
    assert 'headers["X-AI-Admin-Token"] = admin_token' in proxy
    assert '"X-AI-Admin-Token"' in proxy


def test_services_require_trusted_role_and_board_service_rechecks_admin_token():
    board_dependencies = read(ROOT / "board-service" / "app" / "auth" / "dependencies.py")
    user_dependencies = read(ROOT / "user-service" / "app" / "auth" / "dependencies.py")
    user_routes = read(ROOT / "user-service" / "app" / "routes" / "users.py")

    assert 'request.headers.get("X-User-Role") == "admin"' in board_dependencies
    assert "def require_admin" in board_dependencies
    assert "HTTP_403_FORBIDDEN" in board_dependencies
    assert 'request.cookies.get("access_token")' in board_dependencies
    assert 'algorithms=["HS256"]' in board_dependencies
    assert 'os.getenv("ADMIN_USER_IDS", "")' in board_dependencies
    assert "token_user_id != principal.user_id" in board_dependencies
    assert 'request.headers.get("X-User-Role") == "admin"' in user_dependencies
    assert '"role": "admin" if role == "admin" else "user"' in user_routes


def test_admin_user_ids_is_documented_without_a_default_admin():
    env_example = read(ROOT / ".env.example")

    assert "ADMIN_USER_IDS=" in env_example
    assert "ADMIN_USER_IDS=admin" not in env_example
