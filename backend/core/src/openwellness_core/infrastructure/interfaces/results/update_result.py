"""Abstract UpdateResult."""

from abc import ABC, abstractmethod


class UpdateResult(ABC):
    """Abstract base class for UpdateResult."""

    @abstractmethod
    def matched_count(self):
        """Return the number of documents matched by the update query."""

    @abstractmethod
    def modified_count(self):
        """Return the number of documents modified by the update query."""

    @abstractmethod
    def upserted_id(self):
        """Return the ID of the upserted document, if an upsert occurred."""

    @abstractmethod
    def acknowledged(self):
        """Return whether the update operation was acknowledged."""
