"""Couchbase repository for UserStress."""

from typing import List, Type, TypeVar

from ....application.repositories.user_stress_repository import UserStressRepository
from ....domain.models.user_stress import UserStress
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_user import CBUserStress
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository

SomeUserStress = TypeVar("SomeUserStress", bound=UserStress)


class CBUserStressRepository(
    UserStressRepository[SomeUserStress],
    CBBaseRepository[SomeUserStress, CBUserStress],
):
    """Couchbase repository for the UserStress entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeUserStress] = UserStress,
        persistence_type: type[CBUserStress] = CBUserStress,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_user_stresses_in_range(
        self, owner: str, start: str, end: str
    ) -> List[SomeUserStress]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND stressDate BETWEEN $start AND $end "
            f"ORDER BY stressDate, createdAt"
        )
        params = {
            "type": CBUserStress.type,
            "owner": owner,
            "start": start,
            "end": end,
        }
        return self.get_by_query(q, params)

    def get_user_stresses_for_date(
        self, owner: str, date: str
    ) -> List[SomeUserStress]:
        return self.get_user_stresses_in_range(owner, date, date)
