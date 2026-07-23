from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_routes_all_local_browser_api_calls_to_local_gateway():
    http_client = (ROOT / "kingwangjjang-fe/src/api/http.ts").read_text(encoding="utf-8")

    assert "LOCAL_AUTH_PREFIXES" not in http_client
    assert "resolveApiBaseUrl()" in http_client


def test_frontend_routes_local_network_browser_hosts_to_local_gateway():
    api_base_url = (ROOT / "kingwangjjang-fe/src/api/api-base-url.ts").read_text(encoding="utf-8")
    oauth_form = (ROOT / "kingwangjjang-fe/src/auth/components/form-oauth.tsx").read_text(
        encoding="utf-8"
    )

    assert "'0.0.0.0'" in api_base_url
    assert "hostname.startsWith('192.168.')" in api_base_url
    assert "hostname.startsWith('10.')" in api_base_url
    assert "parsed.hostname = browserHostname" in api_base_url
    assert "resolveApiBaseUrl()" in oauth_form
    assert "카카오 로그인" in oauth_form


def test_frontend_get_requests_do_not_force_json_content_type():
    http_client = (ROOT / "kingwangjjang-fe/src/api/http.ts").read_text(encoding="utf-8")

    assert "const headers = new Headers(options.headers);" in http_client
    assert "if (options.body && !headers.has('Content-Type'))" in http_client
    assert "headers.set('Content-Type', 'application/json')" in http_client


def test_frontend_uses_backend_site_label_without_managing_label_mapping():
    board_api = (ROOT / "kingwangjjang-fe/src/api/board-api.ts").read_text(encoding="utf-8")

    assert "siteLabel" in board_api
    assert "site: post.site" in board_api
    assert "siteLabel: post.site_label || post.site" in board_api
    assert "function getSiteLabel" not in board_api
    assert "와이고수" not in board_api
    assert "디시인사이드" not in board_api


def test_frontend_board_site_filter_is_sent_to_board_api():
    board_view = (ROOT / "kingwangjjang-fe/src/sections/board/view/board-view.tsx").read_text(
        encoding="utf-8"
    )
    use_board = (ROOT / "kingwangjjang-fe/src/hooks/use-board.ts").read_text(encoding="utf-8")

    assert "const boardFilters = useMemo" in board_view
    assert "sites: selectedSites" in board_view
    assert "} = useBoard(boardFilters);" in board_view
    assert ".filter((post) => selectedSites.includes(post.site))" not in board_view
    assert "queryFn: getBoardFilterOptions" in use_board
    assert "setFilterCollection" not in use_board
