from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_compose_wires_board_to_internal_gpt_service_without_host_port():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    gpt_service = services["kingwangjjang-gpt-service"]
    assert "ports" not in gpt_service
    assert gpt_service["environment"]["DATABASE_URL"] == "${DOCKER_DATABASE_URL}"
    assert gpt_service["depends_on"]["kingwangjjang-postgres"]["condition"] == (
        "service_healthy"
    )
    assert gpt_service["restart"] == "unless-stopped"
    assert "healthcheck" in gpt_service

    board_service = services["kingwangjjang-board-service"]
    assert board_service["environment"]["AI_SERVICE_URL"] == (
        "http://kingwangjjang-gpt-service:33336"
    )
    assert board_service["depends_on"]["kingwangjjang-gpt-service"]["condition"] == (
        "service_healthy"
    )


def test_ci_builds_and_deploys_gpt_service_image():
    workflow = (ROOT / ".github" / "workflows" / "fastapi.yml").read_text(encoding="utf-8")

    assert "context: ./gpt-service" in workflow
    assert "/gpt-service:0.0.1" in workflow
    assert "AI_SERVICE_TOKEN" in workflow
    assert "AI_NODE_ADMIN_TOKEN" in workflow
    assert 'AI_SERVICE_TOKEN="${AI_SERVICE_TOKEN:-$(python3 -c' in workflow
    assert 'AI_NODE_ADMIN_TOKEN="${AI_NODE_ADMIN_TOKEN:-$(python3 -c' in workflow


def test_gpt_docker_context_excludes_local_environment_files():
    dockerignore = {
        line.strip()
        for line in (ROOT / "gpt-service" / ".dockerignore")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert ".env" in dockerignore
    assert ".env.*" in dockerignore


def test_python_package_initializers_are_not_globally_ignored():
    gitignore_rules = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "__init__.py" not in gitignore_rules
    assert (ROOT / "gpt-service" / "app" / "adapters" / "__init__.py").is_file()
