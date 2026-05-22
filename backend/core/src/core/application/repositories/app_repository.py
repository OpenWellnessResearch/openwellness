"""AppRepository interface."""

from abc import abstractmethod

from ...domain.models.app import App
from .base_crud_repository import BaseCrudRepository


class AppRepository(BaseCrudRepository[App, dict]):
    """Port for the App entity."""

    @abstractmethod
    def create_app(self, name: str, unlistedLink: bool = True) -> App:
        """Create a new App."""
