"""Mongo repository for Admin."""

from ....application.repositories.admin_repository import AdminRepository
from ....domain.models.admin import Admin
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_admin import MongoAdmin
from .mongo_base_repository import MongoBaseRepository


class MongoAdminRepository(AdminRepository, MongoBaseRepository[Admin, MongoAdmin]):
    """Mongo repository for the Admin entity."""

    def __init__(
        self,
        db: CollectionRepository,
        persistence_type: type[MongoAdmin] = MongoAdmin,
    ):
        super().__init__(db, Admin, persistence_type)
        self.entity_type = Admin

    def get_admin(self, admin_id: str) -> Admin | None:
        return self.get_by_id(admin_id)
