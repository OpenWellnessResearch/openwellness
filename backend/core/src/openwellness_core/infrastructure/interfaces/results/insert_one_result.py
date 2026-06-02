"""Abstract InsertOneResult."""

from abc import ABC, abstractmethod
from typing import Any


class InsertOneResult(ABC):
    """Abstract base class for InsertOneResult."""

    @property
    @abstractmethod
    def inserted_id(self) -> Any:
        """The inserted document's _id."""
