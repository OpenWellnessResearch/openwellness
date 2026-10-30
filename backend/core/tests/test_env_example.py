"""FOUND-03: .env.example resolves to localhost values; compose overrides to the redis service.

The example file is loaded through the real settings classes by pointing
OPENWELLNESS_ENV_FILE at it. Real environment variables are cleared so the
test reads the file, not the developer's shell.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from openwellness_core.infrastructure.config.settings import (
    ENV_FILE_VAR,
    RedisSettings,
    resolve_env_file,
)
from openwellness_scheduler.config import CelerySettings

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
COMPOSE = REPO_ROOT / "docker-compose.yml"


def test_env_example_resolves_redis_and_celery_to_localhost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(ENV_FILE_VAR, str(ENV_EXAMPLE))
    env_file = resolve_env_file()
    assert env_file == ENV_EXAMPLE

    # pyright does not see pydantic-settings' init-time ``_env_file`` kwarg.
    redis = RedisSettings(_env_file=env_file)  # type: ignore[call-arg]
    celery = CelerySettings(_env_file=env_file)  # type: ignore[call-arg]
    assert redis.url == "redis://localhost:6379/0"
    assert celery.broker_url == "redis://localhost:6379/0"
    assert celery.result_backend == "redis://localhost:6379/1"


def test_compose_points_api_and_scheduler_at_redis_service() -> None:
    services = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]
    assert "redis" in services
    assert services["api"]["environment"]["REDIS_URL"] == "redis://redis:6379/0"
    scheduler_env = services["scheduler"]["environment"]
    assert scheduler_env["CELERY_BROKER_URL"] == "redis://redis:6379/0"
    assert scheduler_env["CELERY_RESULT_BACKEND"] == "redis://redis:6379/1"
