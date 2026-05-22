"""AdminRepository interface."""

from abc import abstractmethod

from ...domain.models.admin import Admin
from .base_crud_repository import BaseCrudRepository


class AdminRepository(BaseCrudRepository[Admin, dict]):
    """Port for the Admin entity."""

    @abstractmethod
    def get_admin(self, admin_id: str) -> Admin | None:
        """Retrieve an admin by its ID."""
