"""BaseCrudRepository interface."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

Entity = TypeVar("Entity")
Query = TypeVar("Query")


class BaseCrudRepository(ABC, Generic[Entity, Query]):
    """Common CRUD operations for entity repositories."""

    @abstractmethod
    def create(self, entity: Entity) -> Entity:
        """Create an entity."""

    @abstractmethod
    def execute_query(self, query: Query) -> Any:
        """Execute a query."""

    @abstractmethod
    def get_by_id(self, entity_id: str) -> Entity | None:
        """Get an entity by its ID."""

    @abstractmethod
    def get_by_query(self, query: Query) -> list[Entity]:
        """Get entities by a query."""

    @abstractmethod
    def list_all(self) -> list[Entity]:
        """List all entities of this repository's type."""

    @abstractmethod
    def save(self, entity: Entity) -> Entity:
        """Save an entity."""

    @abstractmethod
    def delete(self, entity_id: str) -> Any | None:
        """Delete an entity by its ID."""

    @abstractmethod
    def archive(self, entity_id: str) -> None:
        """Archive an entity by its ID.

        Implementations copy the existing entity into an archive slot
        (collection or type-discriminator) before any retention/deletion logic.
        """

    @abstractmethod
    def unarchive(self, entity_id: str) -> None:
        """Restore an archived entity by its ID.

        Inverse of :meth:`archive`: removes the archive-slot copy so the
        original document is the canonical record again. A no-op (not an
        error) when no archive copy exists.
        """
