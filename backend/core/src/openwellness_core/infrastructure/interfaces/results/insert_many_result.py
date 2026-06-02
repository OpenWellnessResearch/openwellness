"""Abstract InsertManyResult."""

from abc import ABC, abstractmethod


class InsertManyResult(ABC):
    """Abstract base class for InsertManyResult."""

    @abstractmethod
    def inserted_ids(self):
        """Return the list of IDs of the inserted documents."""

    @abstractmethod
    def acknowledged(self):
        """Return whether the insert operation was acknowledged."""
