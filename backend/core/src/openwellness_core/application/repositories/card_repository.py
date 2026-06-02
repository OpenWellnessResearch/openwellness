"""CardRepository interface."""

from typing import Generic, TypeVar

from ...domain.models.card import Card
from .base_crud_repository import BaseCrudRepository

SomeCard = TypeVar("SomeCard", bound=Card)


class CardRepository(BaseCrudRepository[SomeCard, str], Generic[SomeCard]):
    """Interface for Card entity."""
