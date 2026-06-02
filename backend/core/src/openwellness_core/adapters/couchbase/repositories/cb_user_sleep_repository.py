"""Couchbase repository for UserSleep."""

from typing import List, Type, TypeVar

from ....application.repositories.user_sleep_repository import UserSleepRepository
from ....domain.models.user_sleep import UserSleep
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_user import CBUserSleep
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository

SomeUserSleep = TypeVar("SomeUserSleep", bound=UserSleep)


class CBUserSleepRepository(
    UserSleepRepository[SomeUserSleep], CBBaseRepository[SomeUserSleep, CBUserSleep]
):
    """Couchbase repository for the UserSleep entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeUserSleep] = UserSleep,
        persistence_type: type[CBUserSleep] = CBUserSleep,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_user_sleeps_in_range(
        self, owner: str, start: str, end: str
    ) -> List[SomeUserSleep]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND sleepDate BETWEEN $start AND $end "
            f"ORDER BY sleepDate, createdAt"
        )
        params = {
            "type": CBUserSleep.type,
            "owner": owner,
            "start": start,
            "end": end,
        }
        return self.get_by_query(q, params)

    def get_user_sleeps_for_date(self, owner: str, date: str) -> List[SomeUserSleep]:
        return self.get_user_sleeps_in_range(owner, date, date)
