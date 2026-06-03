"""Scheduler service configuration.

Implements ``openwellness_core.infrastructure.config.AppConfigInterface``
so it can be passed straight to the core drivers — exactly like the API's
``AppConfig`` — and adds the Celery-specific knobs the API has no use for.

In Clean Architecture terms this is a *Frameworks & Drivers* detail: it
binds the abstract config ports the inner rings depend on to concrete
environment-backed settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from openwellness_core.infrastructure.config.app_config import AppConfigInterface


class CouchbaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COUCHBASE_", extra="ignore")

    url: str = "couchbase://localhost"
    username: str = "Administrator"
    password: str = "password"
    bucket_name: str = "openwellness"


class SyncGatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNC_GATEWAY_", extra="ignore")

    url: str = "http://localhost:4984/openwellness"

    def get_url(self) -> str:
        return self.url


class MongoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONGO_", extra="ignore")

    url: str = "mongodb://localhost:27017"
    db: str = "openwellness"

    def get_url(self) -> str:
        return self.url


class AppConfig(AppConfigInterface):
    """Concrete config — composes core's protocol-typed sub-settings."""

    def __init__(self) -> None:
        self._couchbase = CouchbaseSettings()
        self._sync_gateway = SyncGatewaySettings()
        self._mongo = MongoSettings()

    @property
    def couchbase(self) -> CouchbaseSettings:
        return self._couchbase

    @property
    def sync_gateway(self) -> SyncGatewaySettings:
        return self._sync_gateway

    @property
    def mongo(self) -> MongoSettings:
        return self._mongo


class CelerySettings(BaseSettings):
    """Broker/result-backend knobs (not part of the core config interface)."""

    model_config = SettingsConfigDict(env_prefix="CELERY_", extra="ignore")

    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    task_default_queue: str = "openwellness"
    timezone: str = "UTC"
