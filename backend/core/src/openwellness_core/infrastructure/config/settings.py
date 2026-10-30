"""Single home for datastore, Redis and shared settings (FOUND-02).

Every service (API, scheduler) imports these classes instead of defining its
own copies, so one ``.env`` drives them all.

* One ``.env`` at the repository root (D-17), whichever directory the process
  starts from. ``OPENWELLNESS_ENV_FILE`` overrides the path.
* Precedence: real environment, then ``.env``, then code defaults (D-18). This
  is pydantic-settings' own source order.
* This module only reads. It never writes a file or mutates ``os.environ``, so
  processes starting together cannot race on configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from openwellness_core.infrastructure.config.app_config import AppConfigInterface

ENV_FILE_VAR = "OPENWELLNESS_ENV_FILE"


def resolve_env_file() -> Path | None:
    """Return the ``.env`` path to load, independent of the working directory.

    Order: the ``OPENWELLNESS_ENV_FILE`` override, then ``<repo root>/.env``,
    then ``None`` (inside the container image, where compose injects env vars).
    """
    override = os.environ.get(ENV_FILE_VAR)
    if override:
        return Path(override)
    # shortcut: repo root is found by the docker-compose.yml marker; update the marker if the compose file is renamed
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").is_file():
            return parent / ".env"
    return None


class OpenWellnessSettings(BaseSettings):
    """Base for every settings class; subclasses only declare ``env_prefix``."""

    model_config = SettingsConfigDict(
        env_file=resolve_env_file(), env_file_encoding="utf-8", extra="ignore"
    )


class CouchbaseSettings(OpenWellnessSettings):
    model_config = SettingsConfigDict(env_prefix="COUCHBASE_")

    url: str = "couchbase://localhost"
    username: str = "Administrator"
    password: str = "password"
    bucket_name: str = "openwellness"


class SyncGatewaySettings(OpenWellnessSettings):
    model_config = SettingsConfigDict(env_prefix="SYNC_GATEWAY_")

    url: str = "http://localhost:4984/openwellness"

    def get_url(self) -> str:
        return self.url


class MongoSettings(OpenWellnessSettings):
    model_config = SettingsConfigDict(env_prefix="MONGO_")

    url: str = "mongodb://localhost:27017"
    db: str = "openwellness"

    def get_url(self) -> str:
        return self.url


class RedisSettings(OpenWellnessSettings):
    """Redis connection settings (used for OTP / rate-limit caching)."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"


class PostgresSettings(OpenWellnessSettings):
    """Postgres connection settings.

    An empty ``url`` means not configured. Repositories start reading it when
    the Postgres backend lands; no default credentials ship.
    """

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    url: str = ""


class AppSettings(OpenWellnessSettings):
    """Default App-entity identifiers stamped on unlisted-link apps.

    Read through pydantic-settings so a repo-root ``.env`` works on direct
    runs; ``os.environ`` alone never sees it.
    """

    model_config = SettingsConfigDict(env_prefix="APP_")

    store_id: str | None = None
    ios_bundle_id: str | None = None
    one_signal_app_id: str | None = None


class AppConfig(AppConfigInterface):
    """Concrete config — composes core's protocol-typed sub-settings."""

    def __init__(self) -> None:
        self._couchbase = CouchbaseSettings()
        self._sync_gateway = SyncGatewaySettings()
        self._mongo = MongoSettings()
        self._postgres = PostgresSettings()

    @property
    def couchbase(self) -> CouchbaseSettings:
        return self._couchbase

    @property
    def sync_gateway(self) -> SyncGatewaySettings:
        return self._sync_gateway

    @property
    def mongo(self) -> MongoSettings:
        return self._mongo

    @property
    def postgres(self) -> PostgresSettings:
        return self._postgres
