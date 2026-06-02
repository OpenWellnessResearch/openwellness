"""Couchbase repository for Conditions."""

from ....application.repositories.condition_repository import (
    ConditionRepository,
    SomeCondition,
)
from ....domain.models.condition import Condition
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_condition import CBCondition
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBConditionRepository(
    ConditionRepository, CBBaseRepository[SomeCondition, CBCondition]
):
    """Couchbase repository for the Condition entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeCondition] = Condition,
        persistence_type: type[CBCondition] = CBCondition,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_owner(self, owner_id: str, arg: int) -> SomeCondition | None:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND week = $week "
            f"ORDER BY week, createdAt DESC"
        )
        params = {
            "type": CBCondition.type,
            "owner": owner_id,
            "week": arg,
        }
        items = self.repo.get_by_query(q, params)
        if len(items) == 1:
            return self.init_entity_valid_fields(items[0])
        elif len(items) > 1:
            raise ValueError(
                f"Multiple Conditions found for owner {owner_id} on week {arg}"
            )
        return None

    def get_for_owner_between(
        self, owner_id: str, start: int, end: int
    ) -> list[SomeCondition]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND week BETWEEN $start AND $end "
            f"ORDER BY week, createdAt DESC"
        )
        params = {
            "type": CBCondition.type,
            "owner": owner_id,
            "start": start,
            "end": end,
        }
        return self.get_by_query(q, params)
