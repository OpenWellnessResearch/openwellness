"""Couchbase base repository for all entities."""

from typing import Any, Generic, Type, TypeVar

from ....application.repositories.base_crud_repository import BaseCrudRepository
from ....domain.exceptions.domain_exception import EntityNotFoundException
from ....domain.models.base_entity import BaseEntity
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_base_entity import CBBaseEntity
from ._query_helpers import bucket_ident

Entity = TypeVar("Entity", bound=BaseEntity)
Persistence = TypeVar("Persistence", bound=CBBaseEntity)


class CBBaseRepository(BaseCrudRepository, Generic[Entity, Persistence]):
    """Base Couchbase repository for all entities."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[Entity],
        persistence_type: Type[Persistence],
    ) -> None:
        self.repo = repo
        self.entity_type = entity_type
        self.persistence_type = persistence_type

    def _to_doc(self, entity: Entity, archived: bool = False) -> dict:
        return self.persistence_type.from_domain(entity, archived=archived).model_dump(
            by_alias=True
        )

    def _from_doc(self, doc: dict) -> Entity:
        return self.persistence_type.model_validate(doc).to_domain(self.entity_type)

    def create(self, entity: Entity) -> Entity:
        result = self.repo.create(self._to_doc(entity))
        return self._from_doc(result)

    def execute_query(self, query: str, params: dict | None = None) -> Any:
        """Execute a N1QL query and return raw dict rows.

        All user-supplied values must be passed via ``params`` (named
        parameters: ``$name`` in ``query``). Only the bucket name and
        allowlisted column identifiers may be interpolated into ``query``.
        """
        return self.repo.get_by_query(query, params)

    def get_by_id(self, entity_id: str) -> Entity | None:
        result = self.repo.get_by_id(entity_id)
        return self._from_doc(result) if result else None

    def get_by_query(
        self, query: str, params: dict | None = None
    ) -> list[Entity]:
        """Execute a N1QL query and rehydrate domain entities from the rows.

        See :meth:`execute_query` for the parameterization contract.
        """
        return [
            self._from_doc(item) for item in self.execute_query(query, params)
        ]

    def list_all(self) -> list[Entity]:
        b = bucket_ident(self.repo.bucket)
        q = f"SELECT b.* FROM {b} AS b WHERE b.type = $type"
        return self.get_by_query(q, {"type": self.persistence_type.type})

    def init_entity_valid_fields(self, data: dict) -> Entity:
        """Create an entity from a wire-format dict (e.g., raw N1QL rows)."""
        return self._from_doc(data)

    def update_entity_valid_fields(self, entity: Entity, data: dict) -> Entity:
        """Apply a wire-format dict's fields onto an existing entity in place."""
        valid = self.entity_type.valid_fields()
        rehydrated = self.persistence_type.model_validate(data).model_dump(
            by_alias=False
        )
        if "rev" in rehydrated:
            rehydrated["_rev"] = rehydrated.pop("rev")
        for key, value in rehydrated.items():
            if key in valid:
                setattr(entity, key, value)
        return entity

    def save(self, entity: Entity) -> Entity:
        result = self.repo.save(self._to_doc(entity))
        return self._from_doc(result)

    def delete(self, entity_id: str) -> None:
        self.repo.delete(entity_id)

    def archive(self, entity_id: str) -> None:
        """Create an archive copy of an entity, leaving the original in place."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundException(f"Entity {entity_id} not found")
        self.repo.create(self._to_doc(entity, archived=True))

    def unarchive(self, entity_id: str) -> None:
        """Drop the archive copy of an entity, if one exists.

        In the Couchbase representation, archiving stores a *new* document
        with ``type = "<EntityType>Archived"`` (see
        :meth:`CBBaseEntity.from_domain`). The original document keeps its
        live ``type``. Unarchive deletes the archived document so a future
        ``archive(...)`` call won't conflict; the original is untouched.
        """
        b = bucket_ident(self.repo.bucket)
        archived_type = f"{self.persistence_type.type}Archived"
        q = (
            f"SELECT META(b).id AS doc_id FROM {b} AS b "
            f"WHERE b.id = $entity_id AND b.type = $archived_type"
        )
        rows = self.repo.get_by_query(
            q, {"entity_id": entity_id, "archived_type": archived_type}
        )
        for row in rows:
            self.repo.delete(row["doc_id"])
