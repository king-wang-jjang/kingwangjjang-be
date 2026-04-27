from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_GATEWAY_APP = ROOT / "api-gateway" / "app"
USER_SERVICE_APP = ROOT / "user-service" / "app"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_gateway_does_not_own_auth_database_or_oauth_flow():
    main = read(API_GATEWAY_APP / "main.py")
    middleware = read(API_GATEWAY_APP / "middlewares" / "auth_middleware.py")
    pyproject = read(ROOT / "api-gateway" / "pyproject.toml")
    python_files = [
        path
        for path in API_GATEWAY_APP.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    gateway_source = "\n".join(read(path) for path in python_files)

    assert "auth_controllers" not in main
    assert "from app.services.auth_services import JWTService" not in middleware
    assert "MongoController" not in gateway_source
    assert "from app.db" not in gateway_source
    assert "pymongo" not in pyproject


def test_gateway_routes_auth_and_user_traffic_to_user_service_prefix():
    routes = read(API_GATEWAY_APP / "routes" / "index.py")

    assert '"userservice/"' in routes
    assert '"login"' in routes
    assert '"callback"' in routes
    assert '"user/":' not in routes
    assert "RedirectResponse(url=response.headers" not in routes
    assert "headers=_response_headers(response)" in routes


def test_user_service_owns_login_callback_and_token_persistence():
    main = read(USER_SERVICE_APP / "main.py")
    auth_route = USER_SERVICE_APP / "routes" / "auth.py"
    auth_service = USER_SERVICE_APP / "services" / "auth_service.py"

    assert auth_route.exists()
    assert auth_service.exists()
    assert "auth_router" in main
    assert '@router.get("/login")' in read(auth_route)
    assert '@router.get("/callback")' in read(auth_route)
    assert "secure=_cookie_secure()" in read(auth_route)
    assert "save_user_to_db" in read(auth_service)
    assert "create_access_token" in read(auth_service)
