"""Abstract Mongo collection repository."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .results import DeleteResult, InsertManyResult, InsertOneResult, UpdateResult


class MongoCollectionRepository(ABC):
    """Abstract base class for a MongoDB collection."""

    @abstractmethod
    def insert_one(self, document) -> InsertOneResult:
        """Insert a single document into the collection."""

    @abstractmethod
    def insert_many(self, documents) -> InsertManyResult:
        """Insert multiple documents into the collection."""

    @abstractmethod
    def find(self, filter=None, *args, **kwargs) -> Iterable:
        """Query the collection."""

    @abstractmethod
    def find_one(self, filter=None, *args, **kwargs) -> dict | None:
        """Find a single document in the collection."""

    @abstractmethod
    def update_one(self, filter, update, *args, **kwargs) -> UpdateResult:
        """Update a single document in the collection."""

    @abstractmethod
    def update_many(self, filter, update, *args, **kwargs) -> UpdateResult:
        """Update multiple documents in the collection."""

    @abstractmethod
    def delete_one(self, filter, *args, **kwargs) -> DeleteResult:
        """Delete a single document from the collection."""

    @abstractmethod
    def delete_many(self, filter, *args, **kwargs) -> DeleteResult:
        """Delete multiple documents from the collection."""

    @abstractmethod
    def count_documents(self, filter, *args, **kwargs) -> int:
        """Count documents in the collection."""
