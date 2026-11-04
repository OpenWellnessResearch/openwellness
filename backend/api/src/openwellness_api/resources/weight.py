"""Weight resource — owner-scoped reference implementation.

Canonical pattern for every owner-scoped resource. The same five AIP
standard methods + ``:undelete`` + ``:purge`` show up here in full so the
HTTP contract is visible per resource. Sister files mirror this skeleton.
"""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import WeightRepository
from openwellness_core.domain.models.weight import Weight as WeightEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    check_parent,
    not_found,
    serialize_many,
    serialize_one,
    stamp_audit,
)
from ..common.pagination import PageParams, page_params, paginate
from ..common.resource_name import format_name
from ..common.time_range import parse_arrow, resolve_time_range
from ..deps.container import container_dep
from ..deps.principal import Principal, get_principal
from ..schemas.weight import Weight, WeightCreate, WeightList, WeightUpdate

_COLLECTION = "weights"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("weight")

    def _fetch(user: str, weight: str, repo: Any) -> Any:
        entity = repo.get_by_id(weight)
        if entity is None:
            not_found(_COLLECTION, weight, parent=_parent_name(user))
        return check_parent(
            entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
        )

    @router.post("", status_code=201, response_model=Weight)
    def create_weight(
        user: str,
        body: WeightCreate,
        principal: Principal = Depends(get_principal),
        repo: WeightRepository = Depends(repo_dep),
    ) -> Any:
        payload = stamp_audit(
            body.model_dump(exclude_unset=False),
            parent_id=user,
            principal=principal,
        )
        entity = WeightEntity(**payload)
        return serialize_one(
            repo.create(entity),
            Weight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{weight}", response_model=Weight)
    def get_weight(
        user: str, weight: str, repo: WeightRepository = Depends(repo_dep)
    ) -> Any:
        return serialize_one(
            _fetch(user, weight, repo),
            Weight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{weight}", response_model=Weight)
    def update_weight(
        user: str,
        weight: str,
        body: WeightUpdate,
        principal: Principal = Depends(get_principal),
        repo: WeightRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, weight, repo)
        apply_patch(entity, body, principal=principal)
        return serialize_one(
            repo.save(entity),
            Weight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{weight}", status_code=204)
    def delete_weight(
        user: str, weight: str, repo: WeightRepository = Depends(repo_dep)
    ) -> None:
        _fetch(user, weight, repo)
        repo.archive(weight)
        return None

    @router.post("/{weight}:undelete", response_model=Weight)
    def undelete_weight(
        user: str, weight: str, repo: WeightRepository = Depends(repo_dep)
    ) -> Any:
        entity = _fetch(user, weight, repo)
        repo.unarchive(weight)
        return serialize_one(
            entity, Weight, collection=_COLLECTION, parent=_parent_name(user)
        )

    @router.post("/{weight}:purge", status_code=204)
    def purge_weight(
        user: str, weight: str, repo: WeightRepository = Depends(repo_dep)
    ) -> None:
        _fetch(user, weight, repo)
        repo.delete(weight)
        return None

    @router.get("", response_model=WeightList)
    def list_weights(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("weight", "list")),
        repo: WeightRepository = Depends(repo_dep),
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
            window, Weight, collection=_COLLECTION, parent=_parent_name(user)
        )
        return {"weights": rows, "nextPageToken": next_token}

    _ = (
        create_weight,
        get_weight,
        update_weight,
        delete_weight,
        undelete_weight,
        purge_weight,
        list_weights,
    )
    return router
