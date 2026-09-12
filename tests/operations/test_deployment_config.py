from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_has_ordered_health_checked_services() -> None:
    configuration = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    )
    services = configuration["services"]

    assert set(services) == {
        "database",
        "migration",
        "api",
        "dashboard",
        "automation",
    }
    assert "ports" not in services["database"]
    assert services["database"]["healthcheck"]["test"] == [
        "CMD",
        "healthcheck.sh",
        "--connect",
        "--innodb_initialized",
    ]
    assert services["api"]["depends_on"]["migration"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["dashboard"]["depends_on"]["api"]["condition"] == (
        "service_healthy"
    )
    assert services["automation"]["profiles"] == ["automation"]


def test_dockerfiles_use_exec_commands_and_non_root_runtime_users() -> None:
    python_dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    frontend_dockerfile = (PROJECT_ROOT / "frontend" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "USER appuser" in python_dockerfile
    assert 'CMD ["python", "-m", "uvicorn"' in python_dockerfile
    assert "USER node" in frontend_dockerfile
    assert 'CMD ["node", "server.js"]' in frontend_dockerfile
