"""Asset resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import AssetRepository
from openwellness_core.domain.models.asset import Asset as AssetEntity

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
from ..schemas.asset import (
    Asset,
    AssetCreate,
    AssetList,
    AssetUpdate,
)

_COLLECTION = "assets"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("asset")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=Asset)
    def create(
        user: str,
        body: AssetCreate,
        access: Access = Depends(authorize("asset", "create")),
        repo: AssetRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(AssetEntity(**payload)),
            Asset,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{asset}", response_model=Asset)
    def get(
        user: str,
        asset: str,
        access: Access = Depends(authorize("asset", "get")),
        repo: AssetRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, asset, repo, access),
            Asset,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{asset}", response_model=Asset)
    def patch(
        user: str,
        asset: str,
        body: AssetUpdate,
        access: Access = Depends(authorize("asset", "patch")),
        repo: AssetRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, asset, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            Asset,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{asset}", status_code=204)
    def delete(
        user: str,
        asset: str,
        access: Access = Depends(authorize("asset", "delete")),
        repo: AssetRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, asset, repo, access)
        repo.archive(asset)
        return None

    @router.post("/{asset}:undelete", response_model=Asset)
    def undelete(
        user: str,
        asset: str,
        access: Access = Depends(authorize("asset", "undelete")),
        repo: AssetRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, asset, repo, access)
        repo.unarchive(asset)
        return serialize_one(
            entity,
            Asset,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{asset}:purge", status_code=204)
    def purge(
        user: str,
        asset: str,
        access: Access = Depends(authorize("asset", "purge")),
        repo: AssetRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, asset, repo, access)
        repo.delete(asset)
        return None

    @router.get("", response_model=AssetList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("asset", "list")),
        repo: AssetRepository = Depends(repo_dep),
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
            Asset,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"assets": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
