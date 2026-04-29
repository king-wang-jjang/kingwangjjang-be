from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dev_shell_scripts_exist_and_start_source_services():
    dev_sh = ROOT / "dev.sh"
    dev_ps1 = ROOT / "dev.ps1"

    assert dev_sh.exists()
    assert dev_ps1.exists()

    sh_content = dev_sh.read_text(encoding="utf-8")
    ps1_content = dev_ps1.read_text(encoding="utf-8")

    for content in (sh_content, ps1_content):
        assert "api-gateway" in content
        assert "user-service" in content
        assert "board-service" in content
        assert "comment-service" in content
        assert "33333" in content
        assert "33334" in content
        assert "33335" in content
        assert "8000" in content
        assert "SERVER_RUN_MODE=FALSE" in content
        assert "AUTH_COOKIE_SECURE=FALSE" in content


def test_dev_scripts_expose_operational_commands():
    sh_content = (ROOT / "dev.sh").read_text(encoding="utf-8")
    ps1_content = (ROOT / "dev.ps1").read_text(encoding="utf-8")

    for content in (sh_content, ps1_content):
        assert "up" in content
        assert "down" in content
        assert "restart" in content
        assert "logs" in content
        assert "ps" in content


def test_dev_scripts_export_database_url_for_local_services():
    sh_content = (ROOT / "dev.sh").read_text(encoding="utf-8")
    ps1_content = (ROOT / "dev.ps1").read_text(encoding="utf-8")

    assert "DATABASE_URL=<from .env>" in sh_content
    assert "DATABASE_URL=<from .env>" in ps1_content
    assert "load_dev_env_file" in sh_content
    assert "Import-DevEnvFile" in ps1_content
