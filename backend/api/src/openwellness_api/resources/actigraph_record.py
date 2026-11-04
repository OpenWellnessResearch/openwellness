"""ActigraphRecord resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import ActigraphRecordRepository
from openwellness_core.domain.models.actigraph_record import ActigraphRecord as ActigraphRecordEntity

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
from ..schemas.actigraph_record import (
    ActigraphRecord,
    ActigraphRecordCreate,
    ActigraphRecordList,
    ActigraphRecordUpdate,
)

_COLLECTION = "actigraphRecords"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("actigraph_record")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=ActigraphRecord)
    def create(
        user: str,
        body: ActigraphRecordCreate,
        access: Access = Depends(authorize("actigraph_record", "create")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(ActigraphRecordEntity(**payload)),
            ActigraphRecord,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{actigraph_record}", response_model=ActigraphRecord)
    def get(
        user: str,
        actigraph_record: str,
        access: Access = Depends(authorize("actigraph_record", "get")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, actigraph_record, repo, access),
            ActigraphRecord,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{actigraph_record}", response_model=ActigraphRecord)
    def patch(
        user: str,
        actigraph_record: str,
        body: ActigraphRecordUpdate,
        access: Access = Depends(authorize("actigraph_record", "patch")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, actigraph_record, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            ActigraphRecord,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{actigraph_record}", status_code=204)
    def delete(
        user: str,
        actigraph_record: str,
        access: Access = Depends(authorize("actigraph_record", "delete")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, actigraph_record, repo, access)
        repo.archive(actigraph_record)
        return None

    @router.post("/{actigraph_record}:undelete", response_model=ActigraphRecord)
    def undelete(
        user: str,
        actigraph_record: str,
        access: Access = Depends(authorize("actigraph_record", "undelete")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, actigraph_record, repo, access)
        repo.unarchive(actigraph_record)
        return serialize_one(
            entity,
            ActigraphRecord,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{actigraph_record}:purge", status_code=204)
    def purge(
        user: str,
        actigraph_record: str,
        access: Access = Depends(authorize("actigraph_record", "purge")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, actigraph_record, repo, access)
        repo.delete(actigraph_record)
        return None

    @router.get("", response_model=ActigraphRecordList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("actigraph_record", "list")),
        repo: ActigraphRecordRepository = Depends(repo_dep),
    ) -> Any:
        rng = resolve_time_range(
            start_time,
            end_time,
            parser=parse_arrow,
            require=True,
            max_span_days=7,
            default_start=arrow.Arrow(1970, 1, 1),
            default_end=arrow.Arrow(2100, 1, 1),
        )
        items = access.scope_list(
            repo.get_for_owner_between(user, rng.start, rng.end)
        )
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            ActigraphRecord,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"actigraphRecords": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
