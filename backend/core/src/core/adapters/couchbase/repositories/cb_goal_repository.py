"""Couchbase repository for Goal."""

from typing import Any, Generic

from arrow import Arrow

from ....application.repositories.goal_repository import GoalRepository, SomeGoal
from ....domain.models.goal import Goal
from ....domain.models.goal.kind import Kind, SomeKind, SomeKindArg
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_goal import CBGoal
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBGoalRepository(
    GoalRepository, CBBaseRepository[SomeGoal, CBGoal], Generic[SomeGoal]
):
    """Couchbase repository for the Goal entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeGoal] = Goal,
        persistence_type: type[CBGoal] = CBGoal,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_owner(self, owner_id: str, arg: Arrow) -> SomeGoal | None:
        q, params = self.generate_query(
            owner_id, arg.floor("day"), arg.ceil("day")
        )
        goals = self.get_by_query(q, params)
        return None if len(goals) == 0 else goals[-1]

    def get_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list:
        q, params = self.generate_query(owner_id, start, end)
        return self.get_by_query(q, params)

    def get_all_for_owner(self, owner_id: str, arg: Arrow) -> list[SomeGoal]:
        q, params = self.generate_query(
            owner_id, arg.floor("day"), arg.ceil("day")
        )
        return self.get_by_query(q, params)

    def get_all_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list[SomeGoal]:
        q, params = self.generate_query(owner_id, start, end, False)
        return self.get_by_query(q, params)

    def get_all_for_owner_by_kind(
        self, owner_id: str, arg: Arrow, kind: SomeKindArg | None = None
    ) -> list[SomeGoal]:
        return self.get_all_for_owner_by_kind_between(
            owner_id, arg.floor("day"), arg.ceil("day"), kind
        )

    def get_all_for_owner_by_kind_between(
        self,
        owner_id: str,
        start: Arrow,
        end: Arrow,
        kind: SomeKindArg | None = None,
    ) -> list[SomeGoal]:
        q, params = self.generate_query_by_kind(owner_id, start, end, kind, False)
        return self.get_by_query(q, params)

    def get_for_owner_by_kind(
        self, owner_id: str, arg: Arrow, kind: SomeKind | None = None
    ) -> SomeGoal | None:
        q, params = self.generate_query_by_kind(
            owner_id, arg.floor("day"), arg.ceil("day"), kind
        )
        goals = self.get_by_query(q, params)
        return None if len(goals) == 0 else goals[-1]

    def get_for_owner_by_kind_between(
        self,
        owner_id: str,
        start: Arrow,
        end: Arrow,
        kind: SomeKind | None = None,
    ) -> list[SomeGoal]:
        q, params = self.generate_query_by_kind(owner_id, start, end, kind)
        return self.get_by_query(q, params)

    def generate_query(
        self,
        owner_id: str,
        start: Arrow,
        end: Arrow,
        group_by_start: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        b = bucket_ident(self.repo.bucket)
        params: dict[str, Any] = {
            "type": CBGoal.type,
            "owner": owner_id,
            "start": start.timestamp(),
            "end": end.timestamp(),
        }
        q = (
            f"SELECT goals.* "
            f"FROM ( "
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND kind is MISSING "
            f"AND startDate BETWEEN $start AND $end "
            f"ORDER BY startDate, createdAt"
            f") AS goals"
        )
        if group_by_start:
            q += (
                f" INNER JOIN ( "
                f"SELECT max(createdAt) AS mostRecent, startDate "
                f"FROM {b} "
                f"WHERE type = $type "
                f"AND owner = $owner "
                f"AND kind is MISSING "
                f"GROUP BY startDate"
                f") maxCat ON goals.startDate = maxCat.startDate "
                f"AND goals.createdAt = maxCat.mostRecent"
            )
        return q, params

    def generate_query_by_kind(
        self,
        owner_id: str,
        start: Arrow,
        end: Arrow,
        kind: SomeKindArg | None,
        group_by_start: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        b = bucket_ident(self.repo.bucket)
        params: dict[str, Any] = {
            "type": CBGoal.type,
            "owner": owner_id,
            "start": start.timestamp(),
            "end": end.timestamp(),
        }
        kind_clause, kind_params = self.generate_kind_expression(kind)
        params.update(kind_params)
        q = (
            f"SELECT goals.* "
            f"FROM ( "
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND startDate BETWEEN $start AND $end "
            f"{kind_clause} "
            f"ORDER BY startDate, createdAt"
            f") AS goals"
        )
        if group_by_start:
            q += (
                f" INNER JOIN ( "
                f"SELECT max(createdAt) AS mostRecent, startDate "
                f"FROM {b} "
                f"WHERE type = $type "
                f"AND owner = $owner "
                f"{kind_clause} "
                f"GROUP BY startDate"
                f") maxCat ON goals.startDate = maxCat.startDate "
                f"AND goals.createdAt = maxCat.mostRecent"
            )
        return q, params

    def generate_kind_expression(
        self, kind: SomeKindArg | None
    ) -> tuple[str, dict[str, Any]]:
        if kind is None:
            return "AND kind IS NOT MISSING", {}
        if isinstance(kind, (Kind, int)):
            return "AND kind = $kind", {"kind": int(kind)}
        if isinstance(kind, list):
            return "AND kind IN $kinds", {"kinds": [int(k) for k in kind]}
        raise Exception(f"Invalid `kind` type: {type(kind)}")
