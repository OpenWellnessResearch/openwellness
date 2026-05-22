"""Minimal application configuration interface used by core drivers.

This is the slice of the larger AppConfigInterface that core needs to
construct its database driver classes. Each service (API, scheduler)
extends this with its own service-specific keys.
"""

from abc import ABC, abstractmethod
from typing import Protocol


class CouchbaseConfig(Protocol):
    """Couchbase connection details used by the SDK cluster client."""

    @property
    def url(self) -> str: ...

    @property
    def username(self) -> str: ...

    @property
    def password(self) -> str: ...

    @property
    def bucket_name(self) -> str: ...


class SyncGatewayConfig(Protocol):
    """Couchbase Sync Gateway HTTP endpoint."""

    def get_url(self) -> str: ...


class MongoConfig(Protocol):
    """MongoDB connection details."""

    def get_url(self) -> str: ...

    @property
    def db(self) -> str: ...


class AppConfigInterface(ABC):
    """Minimal configuration interface required by core drivers."""

    @property
    @abstractmethod
    def couchbase(self) -> CouchbaseConfig:
        """Get the Couchbase configuration."""

    @property
    @abstractmethod
    def sync_gateway(self) -> SyncGatewayConfig:
        """Get the Sync Gateway configuration."""

    @property
    @abstractmethod
    def mongo(self) -> MongoConfig:
        """Get the MongoDB configuration."""
