"""Couchbase repository for PhysicalActivity."""

from typing import List

import arrow

from ....application.repositories.physical_activity_repository import (
    PhysicalActivityRepository,
)
from ....domain.models.physical_activity import PhysicalActivity
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_physical_activity import CBPhysicalActivity
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBPhysicalActivityRepository(
    PhysicalActivityRepository,
    CBBaseRepository[PhysicalActivity, CBPhysicalActivity],
):
    """Couchbase repository for the PhysicalActivity entity."""

    def __init__(
        self,
        repo: EntityRepository,
        persistence_type: type[CBPhysicalActivity] = CBPhysicalActivity,
    ) -> None:
        super().__init__(repo, PhysicalActivity, persistence_type)

    def fetch_all_in_range(
        self, owner: str, start: float, end: float, descending: bool = False
    ) -> List[PhysicalActivity]:
        b = bucket_ident(self.repo.bucket)
        order_dir = "DESC" if descending else "ASC"
        q = (
            f"SELECT {b}.*, META().id, META().xattrs._sync.rev AS _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND dateOfActivity BETWEEN $start AND $end "
            f"ORDER BY dateOfActivity {order_dir}, createdAt {order_dir}"
        )
        params = {
            "type": CBPhysicalActivity.type,
            "owner": owner,
            "start": start,
            "end": end,
        }
        return self.get_by_query(q, params)

    def fetch_for_week_of_date(self, owner: str, date: float) -> List[PhysicalActivity]:
        arrow_date = arrow.get(date).to("local")
        start = arrow_date.floor("week").timestamp()
        end = arrow_date.ceil("week").timestamp()
        return self.fetch_mvpa_in_range(owner, start, end)

    def fetch_for_date(self, owner: str, date: float) -> List[PhysicalActivity]:
        arrow_date = arrow.get(date).to("local")
        start = arrow_date.floor("day").timestamp()
        end = arrow_date.ceil("day").timestamp()
        return self.fetch_mvpa_in_range(owner, start, end)

    def fetch_mvpa_in_range(
        self, owner: str, start: float, end: float
    ) -> List[PhysicalActivity]:
        activities = self.fetch_all_in_range(owner, start, end)
        return [activity for activity in activities if activity.met >= 3]
