"""UserRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.user import User
from .base_crud_repository import BaseCrudRepository

SomeUser = TypeVar("SomeUser", bound=User)


class UserRepository(BaseCrudRepository[SomeUser, dict], Generic[SomeUser]):
    """Interface for the User repository.

    Raises:
        DuplicateEntityException: ``create`` and ``save`` raise it
            (``openwellness_core.application.exceptions``) when a write violates
            a uniqueness constraint such as the unique email index. Adapters
            translate their driver errors into it; callers rely on this
            documented exception only.
    """

    @abstractmethod
    def get_by_email(self, email: str) -> list[SomeUser]:
        """Return users whose stored email equals ``email`` exactly.

        The caller passes an already-normalized email. A list is returned
        because legacy data may hold duplicates; callers treat more than one
        result as ambiguous.
        """
