"""Mongo repository for App."""

from ....application.repositories.app_repository import AppRepository
from ....domain.models.app import App
from ....infrastructure.config.settings import AppSettings
from ...interfaces.collection_repository import CollectionRepository
from ..model.mongo_app import MongoApp
from .mongo_base_repository import MongoBaseRepository


class MongoAppRepository(AppRepository, MongoBaseRepository[App, MongoApp]):
    """Mongo repository for the App entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        persistence_type: type[MongoApp] = MongoApp,
        app_settings: AppSettings | None = None,
    ) -> None:
        super().__init__(mongo_repo, App, persistence_type)
        self.entity_type = App
        self._app_settings = app_settings

    def create_app(self, name: str, unlistedLink: bool = True) -> App:
        # Deployment-specific identifiers come from the environment or the
        # repository-root .env (see .env.example); unset leaves the fields None.
        app = App(name=name)
        if unlistedLink:
            cfg = self._app_settings or AppSettings()
            app.app_store_id = cfg.store_id
            app.ios_bundle_id = cfg.ios_bundle_id
            app.one_signal_app_id = cfg.one_signal_app_id
        return self.create(app)
