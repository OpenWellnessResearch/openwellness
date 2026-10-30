"""Scheduler service configuration.

Re-exports the one shared ``AppConfig`` from
``openwellness_core.infrastructure.config.settings`` (same class the API uses,
loading the same repo-root ``.env``) and adds the Celery-specific knobs the API
has no use for.

In Clean Architecture terms this is a *Frameworks & Drivers* detail: it
binds the abstract config ports the inner rings depend on to concrete
environment-backed settings.
"""

from pydantic_settings import SettingsConfigDict

from openwellness_core.infrastructure.config.settings import (
    AppConfig,
    OpenWellnessSettings,
)

__all__ = ["AppConfig", "CelerySettings"]


class CelerySettings(OpenWellnessSettings):
    """Broker/result-backend knobs (not part of the core config interface)."""

    model_config = SettingsConfigDict(env_prefix="CELERY_")

    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    task_default_queue: str = "openwellness"
    timezone: str = "UTC"
