"""SessionRepository interface."""

from abc import abstractmethod
from typing import List, TypeVar

from ...domain.models.session import Session
from .base_crud_repository import BaseCrudRepository

SomeSession = TypeVar("SomeSession", bound=Session)


class SessionRepository(BaseCrudRepository[SomeSession, str]):
    """Port for the Session entity."""

    @abstractmethod
    def fetch_sessions_in_range(
        self,
        owner: str,
        start: float = 0.0,
        end: float = 9999999999999.9,
        require_session_type: bool = False,
        session_type: int | None = None,
    ) -> List[SomeSession]:
        """Fetch sessions in a time range, optionally by session type."""

    @abstractmethod
    def count_sessions_in_range(
        self,
        owner: str,
        start: float = 0.0,
        end: float = 9999999999999.9,
        require_session_type: bool = False,
        session_type: int | None = None,
    ) -> int:
        """Count sessions in a time range, optionally by session type."""
