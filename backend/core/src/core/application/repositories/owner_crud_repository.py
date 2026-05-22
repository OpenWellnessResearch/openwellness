"""OwnerCrudRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.base_owner_entity import BaseOwnerEntity
from .base_crud_repository import BaseCrudRepository

Entity = TypeVar("Entity", bound=BaseOwnerEntity)
OwnerArg = TypeVar("OwnerArg")


class OwnerCrudRepository(BaseCrudRepository[Entity, str], Generic[Entity, OwnerArg]):
    """Repository operations for entities owned by a participant."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, arg: OwnerArg) -> Entity | None:
        """Fetch the entity for an owner given `arg`."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: OwnerArg, end: OwnerArg
    ) -> list[Entity]:
        """Fetch entities for an owner between `start` and `end`."""
