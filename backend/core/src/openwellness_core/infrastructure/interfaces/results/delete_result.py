"""Abstract DeleteResult."""

from abc import ABC, abstractmethod
from typing import Any, Mapping


class DeleteResult(ABC):
    """Abstract base class for DeleteResult."""

    @property
    @abstractmethod
    def deleted_count(self) -> int:
        """Return the number of documents deleted."""

    @property
    @abstractmethod
    def acknowledged(self) -> bool:
        """Return whether the delete operation was acknowledged."""

    @abstractmethod
    def raw_result(self) -> Mapping[str, Any]:
        """Return the raw result document returned by the server."""
