"""PhysicalActivity resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import PhysicalActivityRepository
from openwellness_core.domain.models.physical_activity import PhysicalActivity as PhysicalActivityEntity

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
from ..common.time_range import parse_arrow, resolve_time_range
from ..deps.container import container_dep
from ..schemas.physical_activity import (
    PhysicalActivity,
    PhysicalActivityCreate,
    PhysicalActivityList,
    PhysicalActivityUpdate,
)

_COLLECTION = "physicalActivities"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("physical_activity")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=PhysicalActivity)
    def create(
        user: str,
        body: PhysicalActivityCreate,
        access: Access = Depends(authorize("physical_activity", "create")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(PhysicalActivityEntity(**payload)),
            PhysicalActivity,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{physical_activity}", response_model=PhysicalActivity)
    def get(
        user: str,
        physical_activity: str,
        access: Access = Depends(authorize("physical_activity", "get")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, physical_activity, repo, access),
            PhysicalActivity,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{physical_activity}", response_model=PhysicalActivity)
    def patch(
        user: str,
        physical_activity: str,
        body: PhysicalActivityUpdate,
        access: Access = Depends(authorize("physical_activity", "patch")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, physical_activity, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            PhysicalActivity,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{physical_activity}", status_code=204)
    def delete(
        user: str,
        physical_activity: str,
        access: Access = Depends(authorize("physical_activity", "delete")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, physical_activity, repo, access)
        repo.archive(physical_activity)
        return None

    @router.post("/{physical_activity}:undelete", response_model=PhysicalActivity)
    def undelete(
        user: str,
        physical_activity: str,
        access: Access = Depends(authorize("physical_activity", "undelete")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, physical_activity, repo, access)
        repo.unarchive(physical_activity)
        return serialize_one(
            entity,
            PhysicalActivity,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{physical_activity}:purge", status_code=204)
    def purge(
        user: str,
        physical_activity: str,
        access: Access = Depends(authorize("physical_activity", "purge")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, physical_activity, repo, access)
        repo.delete(physical_activity)
        return None

    @router.get("", response_model=PhysicalActivityList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("physical_activity", "list")),
        repo: PhysicalActivityRepository = Depends(repo_dep),
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
        items = access.scope_list(repo.get_for_owner_between(user, rng.start, rng.end))
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            PhysicalActivity,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"physicalActivities": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
