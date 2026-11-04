"""FitbitSleep resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import FitbitSleepRepository
from openwellness_core.domain.models.fitbit_sleep import FitbitSleep as FitbitSleepEntity

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
from ..schemas.fitbit_sleep import (
    FitbitSleep,
    FitbitSleepCreate,
    FitbitSleepList,
    FitbitSleepUpdate,
)

_COLLECTION = "fitbitSleeps"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("fitbit_sleep")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=FitbitSleep)
    def create(
        user: str,
        body: FitbitSleepCreate,
        access: Access = Depends(authorize("fitbit_sleep", "create")),
        repo: FitbitSleepRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(FitbitSleepEntity(**payload)),
            FitbitSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{fitbit_sleep}", response_model=FitbitSleep)
    def get(
        user: str,
        fitbit_sleep: str,
        access: Access = Depends(authorize("fitbit_sleep", "get")),
        repo: FitbitSleepRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, fitbit_sleep, repo, access),
            FitbitSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{fitbit_sleep}", response_model=FitbitSleep)
    def patch(
        user: str,
        fitbit_sleep: str,
        body: FitbitSleepUpdate,
        access: Access = Depends(authorize("fitbit_sleep", "patch")),
        repo: FitbitSleepRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, fitbit_sleep, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            FitbitSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{fitbit_sleep}", status_code=204)
    def delete(
        user: str,
        fitbit_sleep: str,
        access: Access = Depends(authorize("fitbit_sleep", "delete")),
        repo: FitbitSleepRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, fitbit_sleep, repo, access)
        repo.archive(fitbit_sleep)
        return None

    @router.post("/{fitbit_sleep}:undelete", response_model=FitbitSleep)
    def undelete(
        user: str,
        fitbit_sleep: str,
        access: Access = Depends(authorize("fitbit_sleep", "undelete")),
        repo: FitbitSleepRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, fitbit_sleep, repo, access)
        repo.unarchive(fitbit_sleep)
        return serialize_one(
            entity,
            FitbitSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{fitbit_sleep}:purge", status_code=204)
    def purge(
        user: str,
        fitbit_sleep: str,
        access: Access = Depends(authorize("fitbit_sleep", "purge")),
        repo: FitbitSleepRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, fitbit_sleep, repo, access)
        repo.delete(fitbit_sleep)
        return None

    @router.get("", response_model=FitbitSleepList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("fitbit_sleep", "list")),
        repo: FitbitSleepRepository = Depends(repo_dep),
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
            FitbitSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"fitbitSleeps": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
