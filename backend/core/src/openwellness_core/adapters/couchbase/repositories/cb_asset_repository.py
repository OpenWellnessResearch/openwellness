"""Couchbase repository for Asset."""

from typing import Any, Generic, List, Optional, Type

from ....application.repositories.asset_repository import AssetRepository, SomeAsset
from ....domain.models.asset import Asset
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_asset import CBAsset
from ._query_helpers import allowed_column, bucket_ident
from .cb_base_repository import CBBaseRepository

_ASSET_ORDER_COLUMNS = frozenset({"createdAt", "updatedAt", "week"})


class CBAssetRepository(
    AssetRepository, CBBaseRepository[SomeAsset, CBAsset], Generic[SomeAsset]
):
    """Repository for the Asset entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeAsset] = Asset,
        persistence_type: type[CBAsset] = CBAsset,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type: Type[SomeAsset] = entity_type

    def fetch(
        self,
        study_id: str,
        kind: Optional[int] = None,
        week: Optional[int] = None,
        orderBy: str = "createdAt",
    ) -> List[SomeAsset]:
        b = bucket_ident(self.repo.bucket)
        order_col = allowed_column(orderBy, _ASSET_ORDER_COLUMNS)
        clauses = ["type = $type", "studyId = $studyId"]
        params: dict[str, Any] = {
            "type": CBAsset.type,
            "studyId": study_id,
        }
        if kind is not None:
            clauses.append("kind = $kind")
            params["kind"] = kind
        if week is not None:
            clauses.append("week = $week")
            params["week"] = week
        q = (
            f"SELECT {b}.*, META().id, META().xattrs._sync.rev AS _rev "
            f"FROM {b} "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY {order_col}"
        )
        return self.get_by_query(q, params)
