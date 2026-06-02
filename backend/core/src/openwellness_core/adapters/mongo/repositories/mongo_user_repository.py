"""Mongo repository for User."""

from typing import Generic

from ....application.repositories.user_repository import SomeUser, UserRepository
from ....domain.models.user import User
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_user import MongoUser
from .mongo_base_repository import MongoBaseRepository


class MongoUserRepository(
    UserRepository, MongoBaseRepository[SomeUser, MongoUser], Generic[SomeUser]
):
    """Mongo repository for the User entity."""

    def __init__(
        self,
        repo: CollectionRepository,
        entity_type: type[SomeUser] = User,
        persistence_type: type[MongoUser] = MongoUser,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type
