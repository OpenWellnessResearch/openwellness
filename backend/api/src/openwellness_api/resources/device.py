"""Device resource — top-level."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import DeviceRepository
from openwellness_core.domain.models.device import Device as DeviceEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..deps.container import container_dep
from ..schemas.device import (
    Device,
    DeviceCreate,
    DeviceList,
    DeviceUpdate,
)

_COLLECTION = "devices"


def build_router() -> APIRouter:
    router = APIRouter(prefix=f"/{_COLLECTION}", tags=[_COLLECTION])
    repo_dep = container_dep("device")

    def _fetch(id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_)
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=Device)
    def create(
        body: DeviceCreate,
        access: Access = Depends(authorize("device", "create")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> Any:
        payload = body.model_dump(exclude_unset=False)
        return serialize_one(
            repo.create(DeviceEntity(**payload)),
            Device,
            collection=_COLLECTION,
        )

    @router.get("/{device}", response_model=Device)
    def get(
        device: str,
        access: Access = Depends(authorize("device", "get")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(device, repo, access), Device, collection=_COLLECTION
        )

    @router.patch("/{device}", response_model=Device)
    def patch(
        device: str,
        body: DeviceUpdate,
        access: Access = Depends(authorize("device", "patch")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(device, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity), Device, collection=_COLLECTION
        )

    @router.delete("/{device}", status_code=204)
    def delete(
        device: str,
        access: Access = Depends(authorize("device", "delete")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> None:
        _fetch(device, repo, access)
        repo.archive(device)
        return None

    @router.post("/{device}:undelete", response_model=Device)
    def undelete(
        device: str,
        access: Access = Depends(authorize("device", "undelete")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(device, repo, access)
        repo.unarchive(device)
        return serialize_one(entity, Device, collection=_COLLECTION)

    @router.post("/{device}:purge", status_code=204)
    def purge(
        device: str,
        access: Access = Depends(authorize("device", "purge")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> None:
        _fetch(device, repo, access)
        repo.delete(device)
        return None

    @router.get("", response_model=DeviceList)
    def list_items(
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("device", "list")),
        repo: DeviceRepository = Depends(repo_dep),
    ) -> Any:
        items = access.scope_list(repo.list_all())
        window, next_token = paginate(items, params)
        rows = serialize_many(window, Device, collection=_COLLECTION)
        return {"devices": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
