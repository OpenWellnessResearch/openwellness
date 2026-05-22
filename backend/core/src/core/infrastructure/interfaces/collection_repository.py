"""Abstract Mongo database wrapper."""

from abc import ABC, abstractmethod

from .mongo_collection_repository import MongoCollectionRepository


class CollectionRepository(ABC):
    """Abstract base class for a MongoDB database."""

    @abstractmethod
    def __getattr__(self, name) -> MongoCollectionRepository:
        """Dynamically access collections as attributes."""

    @abstractmethod
    def __getitem__(self, name) -> MongoCollectionRepository:
        """Access collections as items."""

    @abstractmethod
    def list_collection_names(self, *args, **kwargs):
        """List all collection names in the database."""

    @abstractmethod
    def create_collection(self, name, *args, **kwargs):
        """Create a new collection in the database."""

    @abstractmethod
    def drop_collection(self, name_or_collection, *args, **kwargs):
        """Drop a collection by name or collection instance."""

    @abstractmethod
    def command(self, command, *args, **kwargs):
        """Run a database command."""
