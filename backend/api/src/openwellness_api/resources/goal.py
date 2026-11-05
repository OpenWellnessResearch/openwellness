"""Goal resource — owner-scoped, discriminated union (Weekly | Daily | Legacy).

List supports ``filter=kind=N`` via :func:`parse_filter`, dispatched to the
kind-aware repository method when ``kind`` is present.
"""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import GoalRepository
from openwellness_core.domain.models.goal import (
    DailyGoal,
    Goal as GoalEntity,
    LegacyGoal,
    WeeklyGoal,
)

from ..authz.engine import Access, authorize
from ..common.filter import parse_filter
from ..common.handlers import (
    apply_patch,
    check_parent,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..common.resource_name import format_name
from ..common.time_range import parse_arrow, resolve_time_range
from ..deps.container import container_dep
from ..schemas.goal import (
    DailyGoalCreate,
    Goal,
    GoalCreate,
    GoalList,
    GoalUpdate,
    LegacyGoalCreate,
    WeeklyGoalCreate,
)

_COLLECTION = "goals"
_PARENT = "users"
_FILTERABLE = {"kind": int}


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def _build_goal(body: Any, user: str, access: Access) -> GoalEntity:
    payload = access.stamp_create(body.model_dump(exclude_unset=False), parent_id=user)
    if isinstance(body, WeeklyGoalCreate):
        cls: type[GoalEntity] = WeeklyGoal
    elif isinstance(body, DailyGoalCreate):
        cls = DailyGoal
    elif isinstance(body, LegacyGoalCreate):
        cls = LegacyGoal
        payload.pop("kind", None)  # LegacyGoal has no ``kind`` field
    else:
        cls = GoalEntity
    return cls(**payload)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("goal")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=Goal)
    def create(
        user: str,
        body: GoalCreate,
        access: Access = Depends(authorize("goal", "create")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            repo.create(_build_goal(body, user, access)),
            Goal,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{goal}", response_model=Goal)
    def get(
        user: str,
        goal: str,
        access: Access = Depends(authorize("goal", "get")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, goal, repo, access),
            Goal,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{goal}", response_model=Goal)
    def patch(
        user: str,
        goal: str,
        body: GoalUpdate,
        access: Access = Depends(authorize("goal", "patch")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, goal, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            Goal,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{goal}", status_code=204)
    def delete(
        user: str,
        goal: str,
        access: Access = Depends(authorize("goal", "delete")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, goal, repo, access)
        repo.archive(goal)
        return None

    @router.post("/{goal}:undelete", response_model=Goal)
    def undelete(
        user: str,
        goal: str,
        access: Access = Depends(authorize("goal", "undelete")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, goal, repo, access)
        repo.unarchive(goal)
        return serialize_one(
            entity, Goal, collection=_COLLECTION, parent=_parent_name(user)
        )

    @router.post("/{goal}:purge", status_code=204)
    def purge(
        user: str,
        goal: str,
        access: Access = Depends(authorize("goal", "purge")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, goal, repo, access)
        repo.delete(goal)
        return None

    @router.get("", response_model=GoalList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        filter: str | None = Query(default=None),  # AIP-160
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("goal", "list")),
        repo: GoalRepository = Depends(repo_dep),
    ) -> Any:
        rng = resolve_time_range(
            start_time,
            end_time,
            parser=parse_arrow,
            require=False,
            max_span_days=None,
            default_start=arrow.Arrow(1970, 1, 1),
            default_end=arrow.Arrow(2100, 1, 1),
        )
        # Scope first (D-08): a coach's study filter runs on the unfiltered owner
        # list, so filter= can only narrow what the caller may already see.
        scoped = access.scope_list(
            repo.get_all_for_owner_between(user, rng.start, rng.end)
        )
        parsed = parse_filter(filter, allowed_fields=_FILTERABLE)
        if "kind" in parsed:
            # The kind query may be a second round trip; intersecting keeps the
            # repository's kind semantics, since LegacyGoal has no ``kind``.
            by_kind = repo.get_all_for_owner_by_kind_between(
                user, rng.start, rng.end, kind=parsed["kind"]
            )
            allowed = {g.id for g in scoped}
            results = [g for g in by_kind if g.id in allowed]
        else:
            results = scoped
        window, next_token = paginate(results, params)
        rows = serialize_many(
            window, Goal, collection=_COLLECTION, parent=_parent_name(user)
        )
        return {"goals": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
