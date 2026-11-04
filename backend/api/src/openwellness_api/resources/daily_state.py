"""DailyState resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import DailyStateRepository
from openwellness_core.domain.models.daily_state import DailyState as DailyStateEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    check_parent,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..common.resource_name import format_name
from ..common.time_range import parse_str, resolve_time_range
from ..deps.container import container_dep
from ..schemas.daily_state import (
    DailyState,
    DailyStateCreate,
    DailyStateList,
    DailyStateUpdate,
)

_COLLECTION = "dailyStates"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("daily_state")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=DailyState)
    def create(
        user: str,
        body: DailyStateCreate,
        access: Access = Depends(authorize("daily_state", "create")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(DailyStateEntity(**payload)),
            DailyState,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{daily_state}", response_model=DailyState)
    def get(
        user: str,
        daily_state: str,
        access: Access = Depends(authorize("daily_state", "get")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, daily_state, repo, access),
            DailyState,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{daily_state}", response_model=DailyState)
    def patch(
        user: str,
        daily_state: str,
        body: DailyStateUpdate,
        access: Access = Depends(authorize("daily_state", "patch")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, daily_state, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            DailyState,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{daily_state}", status_code=204)
    def delete(
        user: str,
        daily_state: str,
        access: Access = Depends(authorize("daily_state", "delete")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, daily_state, repo, access)
        repo.archive(daily_state)
        return None

    @router.post("/{daily_state}:undelete", response_model=DailyState)
    def undelete(
        user: str,
        daily_state: str,
        access: Access = Depends(authorize("daily_state", "undelete")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, daily_state, repo, access)
        repo.unarchive(daily_state)
        return serialize_one(
            entity,
            DailyState,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{daily_state}:purge", status_code=204)
    def purge(
        user: str,
        daily_state: str,
        access: Access = Depends(authorize("daily_state", "purge")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, daily_state, repo, access)
        repo.delete(daily_state)
        return None

    @router.get("", response_model=DailyStateList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("daily_state", "list")),
        repo: DailyStateRepository = Depends(repo_dep),
    ) -> Any:
        rng = resolve_time_range(
            start_time,
            end_time,
            parser=parse_str,
            require=False,
            max_span_days=None,
            default_start="1970-01-01",
            default_end="2100-01-01",
        )
        items = access.scope_list(repo.get_for_owner_between(user, rng.start, rng.end))
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            DailyState,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"dailyStates": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
