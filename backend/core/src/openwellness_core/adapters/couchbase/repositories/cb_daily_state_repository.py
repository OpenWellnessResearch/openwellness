"""Couchbase repository for DailyState."""

from arrow import Arrow

from ....application.repositories.daily_state_repository import (
    DailyStateRepository,
    SomeDailyState,
)
from ....domain.models.daily_state import DailyState
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_daily_state import CBDailyState
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBDailyStateRepository(
    DailyStateRepository, CBBaseRepository[SomeDailyState, CBDailyState]
):
    """Couchbase repository for the DailyState entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeDailyState] = DailyState,
        persistence_type: type[CBDailyState] = CBDailyState,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_owner(self, owner_id: str, arg: Arrow) -> SomeDailyState | None:
        items = self.get_for_owner_between(owner_id, arg, arg)
        return items[0] if len(items) == 1 else None

    def get_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list[SomeDailyState]:
        q, params = self._build_get_between_query(owner_id, start, end)
        items = self.repo.get_by_query(q, params)
        return [self.init_entity_valid_fields(item) for item in items]

    def _build_get_between_query(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> tuple[str, dict]:
        ymd = "YYYY-MM-DD"
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND date BETWEEN $start AND $end "
            f"ORDER BY date, createdAt"
        )
        params = {
            "type": CBDailyState.type,
            "owner": owner_id,
            "start": start.format(ymd),
            "end": end.format(ymd),
        }
        return q, params
