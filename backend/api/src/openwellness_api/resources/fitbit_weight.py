"""FitbitWeight resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import FitbitWeightRepository
from openwellness_core.domain.models.fitbit_weight import FitbitWeight as FitbitWeightEntity

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
from ..schemas.fitbit_weight import (
    FitbitWeight,
    FitbitWeightCreate,
    FitbitWeightList,
    FitbitWeightUpdate,
)

_COLLECTION = "fitbitWeights"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("fitbit_weight")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=FitbitWeight)
    def create(
        user: str,
        body: FitbitWeightCreate,
        access: Access = Depends(authorize("fitbit_weight", "create")),
        repo: FitbitWeightRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(FitbitWeightEntity(**payload)),
            FitbitWeight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{fitbit_weight}", response_model=FitbitWeight)
    def get(
        user: str,
        fitbit_weight: str,
        access: Access = Depends(authorize("fitbit_weight", "get")),
        repo: FitbitWeightRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, fitbit_weight, repo, access),
            FitbitWeight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{fitbit_weight}", response_model=FitbitWeight)
    def patch(
        user: str,
        fitbit_weight: str,
        body: FitbitWeightUpdate,
        access: Access = Depends(authorize("fitbit_weight", "patch")),
        repo: FitbitWeightRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, fitbit_weight, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            FitbitWeight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{fitbit_weight}", status_code=204)
    def delete(
        user: str,
        fitbit_weight: str,
        access: Access = Depends(authorize("fitbit_weight", "delete")),
        repo: FitbitWeightRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, fitbit_weight, repo, access)
        repo.archive(fitbit_weight)
        return None

    @router.post("/{fitbit_weight}:undelete", response_model=FitbitWeight)
    def undelete(
        user: str,
        fitbit_weight: str,
        access: Access = Depends(authorize("fitbit_weight", "undelete")),
        repo: FitbitWeightRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, fitbit_weight, repo, access)
        repo.unarchive(fitbit_weight)
        return serialize_one(
            entity,
            FitbitWeight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{fitbit_weight}:purge", status_code=204)
    def purge(
        user: str,
        fitbit_weight: str,
        access: Access = Depends(authorize("fitbit_weight", "purge")),
        repo: FitbitWeightRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, fitbit_weight, repo, access)
        repo.delete(fitbit_weight)
        return None

    @router.get("", response_model=FitbitWeightList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("fitbit_weight", "list")),
        repo: FitbitWeightRepository = Depends(repo_dep),
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
        items = access.scope_list(
            repo.get_for_owner_between(user, rng.start, rng.end)
        )
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            FitbitWeight,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"fitbitWeights": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
