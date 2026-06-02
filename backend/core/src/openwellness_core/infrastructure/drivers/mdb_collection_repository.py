"""MongoDB database wrapper."""

from pymongo import MongoClient

from ..config.app_config import AppConfigInterface
from ..interfaces.collection_repository import CollectionRepository


class MDBCollectionRepository(CollectionRepository):
    """Thin wrapper around a pymongo database handle."""

    def __init__(self, config: AppConfigInterface) -> None:
        super().__init__()
        mdb_config = config.mongo
        mongo = MongoClient(mdb_config.get_url())
        self.db = getattr(mongo, mdb_config.db)

    def __getattr__(self, name):
        return getattr(self.db, name)

    def __getitem__(self, name):
        return self.db[name]

    def list_collection_names(self, *args, **kwargs):
        return self.db.list_collection_names(*args, **kwargs)

    def create_collection(self, name, *args, **kwargs):
        return self.db.create_collection(name, *args, **kwargs)

    def drop_collection(self, name_or_collection, *args, **kwargs):
        return self.db.drop_collection(name_or_collection, *args, **kwargs)

    def command(self, command, *args, **kwargs):
        return self.db.command(command, *args, **kwargs)

    def __repr__(self):
        return f"MongoRepository({self})"

    def __str__(self):
        return f"MongoRepository({self})"
