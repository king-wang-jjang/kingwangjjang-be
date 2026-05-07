from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_root_dev_all_starts_crawler_process():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "$CrawlerDir = Join-Path $RootDir 'CrawlScheduler'" in script
    assert "function Start-CrawlerService" in script
    assert "Ensure-PythonProjectVenv -ProjectDir $CrawlerDir" in script
    assert "crawl_scheduler/main.py" in script
    assert "crawler.log" in script
    assert "crawler.err.log" in script
    assert "-FilePath $pythonRunner" in script
    assert "Write-PidRecord -Name 'crawler'" in script
    assert "Start-CrawlerService" in script


def test_root_dev_all_installs_crawler_dependencies_without_editable_package():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "$CrawlerDependencies = @(" in script
    assert "schedule" in script
    assert "psycopg[binary]" in script
    assert "crawler-pip.log" in script
    assert "-FilePath $venvPython" in script
    assert "-m pip install -e $ProjectDir" not in script


def test_root_dev_all_uses_local_api_gateway_port_from_frontend_env():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "@{ Name = 'api-gateway'; Port = 33330 }" in script


def test_root_dev_all_prefers_project_virtualenvs_over_poetry_executable():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "function Resolve-PythonExecutable" in script
    assert ".venv\\Scripts\\python.exe" in script
    assert "-m uvicorn app.main:app" in script
    assert "poetry run uvicorn" not in script


def test_root_dev_all_stop_process_tree_ignores_already_exited_processes():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "Stop-Process -Id $PidValue -Force -ErrorAction SilentlyContinue" in script


def test_root_dev_all_usage_mentions_crawler():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "Start backend services, frontend, and crawler" in script


def test_root_dev_all_sets_crawler_ai_timeout_and_root_env():
    script = (ROOT / "dev-all.ps1").read_text(encoding="utf-8")

    assert "OLLAMA_TIMEOUT_SECONDS" in script
    assert "60" in script
    assert "ROOT" in script
    assert "$CrawlerDir" in script
