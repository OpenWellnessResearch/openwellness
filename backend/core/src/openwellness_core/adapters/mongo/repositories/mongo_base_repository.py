"""Mongo base repository for all entities."""

from typing import Any, Generic, Type, TypeVar

from bson import ObjectId

from ....application.repositories.base_crud_repository import BaseCrudRepository
from ....domain.exceptions.domain_exception import EntityNotFoundException
from ....domain.models.base_entity import BaseEntity
from ...exceptions import AdapterException
from ...interfaces.collection_repository import CollectionRepository
from ...interfaces.results.delete_result import DeleteResult
from ..model.mongo_base_entity import MongoBaseEntity

Entity = TypeVar("Entity", bound=BaseEntity)
Persistence = TypeVar("Persistence", bound=MongoBaseEntity)


def object_id_or_none(value: Any) -> ObjectId | None:
    """Parse ``value`` as an ObjectId, or None when it cannot be one.

    A value Mongo cannot parse names no document, so callers treat it as not found.
    """
    return ObjectId(value) if ObjectId.is_valid(value) else None


class MongoBaseRepository(BaseCrudRepository, Generic[Entity, Persistence]):
    """Base Mongo repository for all entities."""

    def __init__(
        self,
        repo: CollectionRepository,
        entity_type: Type[Entity],
        persistence_type: Type[Persistence],
    ) -> None:
        self.repo = repo
        self.entity_type = entity_type
        self.persistence_type = persistence_type

    @property
    def _collection_name(self) -> str:
        return self.persistence_type.collection

    def _to_doc(self, entity: Entity) -> dict:
        return self.persistence_type.from_domain(entity).model_dump(by_alias=True)

    def _from_doc(self, doc: dict) -> Entity:
        return self.persistence_type.model_validate(doc).to_domain(self.entity_type)

    def create(self, entity: Entity) -> Entity:
        collection = self.repo[self._collection_name]
        result = collection.insert_one(self._to_doc(entity))
        entity.id = str(result.inserted_id)
        fetched = collection.find_one({"_id": result.inserted_id})
        if fetched is None:
            raise AdapterException(
                f"Failed to fetch the created entity with ID {result.inserted_id}"
            )
        return self._from_doc(fetched)

    def execute_query(self, query: dict) -> Any:
        collection = self.repo[self._collection_name]
        return collection.find(query)

    def get_by_id(self, entity_id: str) -> Entity | None:
        oid = object_id_or_none(entity_id)
        if oid is None:
            return None
        result = self.repo[self._collection_name].find_one({"_id": oid})
        return None if not result else self._from_doc(result)

    def get_by_query(self, query: dict) -> list[Entity]:
        return [self._from_doc(item) for item in self.execute_query(query)]

    def list_all(self) -> list[Entity]:
        return self.get_by_query({})

    def init_entity_valid_fields(self, data: dict) -> Entity:
        return self._from_doc(data)

    def save(self, entity: Entity) -> Entity:
        if not entity.id:
            return self.create(entity)
        oid = object_id_or_none(entity.id)
        if oid is None:
            raise EntityNotFoundException(f"Entity {entity.id} not found")
        collection = self.repo[self._collection_name]
        collection.update_one({"_id": oid}, {"$set": self._to_doc(entity)})
        return entity

    def delete(self, entity_id: str) -> DeleteResult:
        oid = object_id_or_none(entity_id)
        if oid is None:
            raise EntityNotFoundException(f"Entity {entity_id} not found")
        return self.repo[self._collection_name].delete_one({"_id": oid})

    def archive(self, entity_id: str) -> None:
        """Insert a copy of the entity into the `{collection}_archive` collection.

        Leaves the original document in place; archiving is a copy, not a move.
        Callers that want move semantics should call `delete(entity_id)` after
        `archive(entity_id)`.
        """
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundException(f"Entity {entity_id} not found")
        archive_collection_name = f"{self._collection_name}_archive"
        self.repo[archive_collection_name].insert_one(self._to_doc(entity))

    def unarchive(self, entity_id: str) -> None:
        """Drop archive copies of an entity from ``{collection}_archive``.

        Inverse of :meth:`archive`: deletes archive-collection rows that
        share the original ``_id``. The original collection's document is
        untouched. No-op when no archive row exists or the id is malformed;
        datastore errors propagate.
        """
        oid = object_id_or_none(entity_id)
        if oid is None:
            return
        self.repo[f"{self._collection_name}_archive"].delete_many({"_id": oid})
