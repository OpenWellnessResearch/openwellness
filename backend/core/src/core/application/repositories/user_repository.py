"""UserRepository interface."""

from typing import Generic, TypeVar

from ...domain.models.user import User
from .base_crud_repository import BaseCrudRepository

SomeUser = TypeVar("SomeUser", bound=User)


class UserRepository(BaseCrudRepository[SomeUser, dict], Generic[SomeUser]):
    """Interface for the User repository."""
