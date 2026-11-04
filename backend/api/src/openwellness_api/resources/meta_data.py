"""MetaData resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import MetaDataRepository
from openwellness_core.domain.models.meta_data import MetaData as MetaDataEntity

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
from ..schemas.meta_data import (
    MetaData,
    MetaDataCreate,
    MetaDataList,
    MetaDataUpdate,
)

_COLLECTION = "metaData"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("meta_data")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=MetaData)
    def create(
        user: str,
        body: MetaDataCreate,
        access: Access = Depends(authorize("meta_data", "create")),
        repo: MetaDataRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(MetaDataEntity(**payload)),
            MetaData,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{meta_data}", response_model=MetaData)
    def get(
        user: str,
        meta_data: str,
        access: Access = Depends(authorize("meta_data", "get")),
        repo: MetaDataRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, meta_data, repo, access),
            MetaData,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{meta_data}", response_model=MetaData)
    def patch(
        user: str,
        meta_data: str,
        body: MetaDataUpdate,
        access: Access = Depends(authorize("meta_data", "patch")),
        repo: MetaDataRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, meta_data, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            MetaData,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{meta_data}", status_code=204)
    def delete(
        user: str,
        meta_data: str,
        access: Access = Depends(authorize("meta_data", "delete")),
        repo: MetaDataRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, meta_data, repo, access)
        repo.archive(meta_data)
        return None

    @router.post("/{meta_data}:undelete", response_model=MetaData)
    def undelete(
        user: str,
        meta_data: str,
        access: Access = Depends(authorize("meta_data", "undelete")),
        repo: MetaDataRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, meta_data, repo, access)
        repo.unarchive(meta_data)
        return serialize_one(
            entity,
            MetaData,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{meta_data}:purge", status_code=204)
    def purge(
        user: str,
        meta_data: str,
        access: Access = Depends(authorize("meta_data", "purge")),
        repo: MetaDataRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, meta_data, repo, access)
        repo.delete(meta_data)
        return None

    @router.get("", response_model=MetaDataList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("meta_data", "list")),
        repo: MetaDataRepository = Depends(repo_dep),
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
            MetaData,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"metaData": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
