"""Couchbase repository for Weight."""

from typing import Type, TypeVar

from arrow import Arrow

from ....application.repositories.weight_repository import WeightRepository
from ....domain.models.weight import Weight
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_weight import CBWeight
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository

SomeWeight = TypeVar("SomeWeight", bound=Weight)


class CBWeightRepository(
    WeightRepository[SomeWeight], CBBaseRepository[SomeWeight, CBWeight]
):
    """Couchbase repository for the Weight entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeWeight] = Weight,
        persistence_type: type[CBWeight] = CBWeight,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_owner(self, owner: str, date: Arrow) -> list[SomeWeight]:
        start = date.floor("day")
        end = date.ceil("day")
        return self.get_for_owner_between(owner, start, end)

    def get_for_owner_between(
        self, owner: str, start: Arrow, end: Arrow
    ) -> list[SomeWeight]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND createdAt BETWEEN $start AND $end "
            f"ORDER BY createdAt ASC"
        )
        params = {
            "type": CBWeight.type,
            "owner": owner,
            "start": start.timestamp(),
            "end": end.timestamp(),
        }
        return self.get_by_query(q, params)
