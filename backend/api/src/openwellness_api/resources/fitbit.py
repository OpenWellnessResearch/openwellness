"""Fitbit resource — top-level."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import FitbitRepository
from openwellness_core.domain.models.fitbit import Fitbit as FitbitEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    not_found,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..deps.container import container_dep
from ..schemas.fitbit import (
    Fitbit,
    FitbitCreate,
    FitbitList,
    FitbitUpdate,
)

_COLLECTION = "fitbits"


def _wire(entity: Any, access: Access) -> dict[str, Any]:
    """The one place a Fitbit is serialized: OAuth tokens leave the server for admins only.

    Today only ``get`` reaches a non-admin, but every path goes through here so a
    later policy change cannot start leaking tokens (ADR 0007 Fitbit response filter).
    """
    wire = serialize_one(entity, Fitbit, collection=_COLLECTION)
    if not access.principal.is_admin:
        wire["accessToken"] = None
        wire["refreshToken"] = None
    return wire


def build_router() -> APIRouter:
    router = APIRouter(prefix=f"/{_COLLECTION}", tags=[_COLLECTION])
    repo_dep = container_dep("fitbit")

    def _fetch(id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_)
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=Fitbit)
    def create(
        body: FitbitCreate,
        access: Access = Depends(authorize("fitbit", "create")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> Any:
        payload = body.model_dump(exclude_unset=False)
        return _wire(repo.create(FitbitEntity(**payload)), access)

    @router.get("/{fitbit}", response_model=Fitbit)
    def get(
        fitbit: str,
        access: Access = Depends(authorize("fitbit", "get")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> Any:
        return _wire(_fetch(fitbit, repo, access), access)

    @router.patch("/{fitbit}", response_model=Fitbit)
    def patch(
        fitbit: str,
        body: FitbitUpdate,
        access: Access = Depends(authorize("fitbit", "patch")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(fitbit, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return _wire(repo.save(entity), access)

    @router.delete("/{fitbit}", status_code=204)
    def delete(
        fitbit: str,
        access: Access = Depends(authorize("fitbit", "delete")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> None:
        _fetch(fitbit, repo, access)
        repo.archive(fitbit)
        return None

    @router.post("/{fitbit}:undelete", response_model=Fitbit)
    def undelete(
        fitbit: str,
        access: Access = Depends(authorize("fitbit", "undelete")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(fitbit, repo, access)
        repo.unarchive(fitbit)
        return _wire(entity, access)

    @router.post("/{fitbit}:purge", status_code=204)
    def purge(
        fitbit: str,
        access: Access = Depends(authorize("fitbit", "purge")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> None:
        _fetch(fitbit, repo, access)
        repo.delete(fitbit)
        return None

    @router.get("", response_model=FitbitList)
    def list_items(
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("fitbit", "list")),
        repo: FitbitRepository = Depends(repo_dep),
    ) -> Any:
        items = access.scope_list(repo.list_all())
        window, next_token = paginate(items, params)
        rows = [_wire(e, access) for e in window]
        return {"fitbits": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
