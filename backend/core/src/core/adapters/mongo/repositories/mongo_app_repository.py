"""Mongo repository for App."""

from ....application.repositories.app_repository import AppRepository
from ....domain.models.app import App
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_app import MongoApp
from .mongo_base_repository import MongoBaseRepository


class MongoAppRepository(AppRepository, MongoBaseRepository[App, MongoApp]):
    """Mongo repository for the App entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        persistence_type: type[MongoApp] = MongoApp,
    ) -> None:
        super().__init__(mongo_repo, App, persistence_type)
        self.entity_type = App

    def create_app(self, name: str, unlistedLink: bool = True) -> App:
        app = App(name=name)
        if unlistedLink:
            app.app_store_id = "1659933622"
            app.ios_bundle_id = "edu.northwestern.CATALYST"
            app.one_signal_app_id = "43ea134a-f78d-4a94-aea6-34cac370650b"
        return self.create(app)
