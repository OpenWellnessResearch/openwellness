"""Study resource — top-level with AIP-136 ``:lookup`` custom method."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import StudyRepository
from openwellness_core.domain.models.study import Study as StudyEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..deps.container import container_dep
from ..schemas.study import (
    Study,
    StudyCreate,
    StudyList,
    StudyLookup,
    StudyUpdate,
)

_COLLECTION = "studies"


def build_router() -> APIRouter:
    router = APIRouter(prefix=f"/{_COLLECTION}", tags=[_COLLECTION])
    repo_dep = container_dep("study")

    def _fetch(id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_)
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=Study)
    def create(
        body: StudyCreate,
        access: Access = Depends(authorize("study", "create")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> Any:
        payload = body.model_dump(exclude_unset=False)
        payload["updated_by"] = access.principal.id  # the wire accepts it (AUTH-06)
        entity = StudyEntity(**payload)
        return serialize_one(repo.create(entity), Study, collection=_COLLECTION)

    @router.get("/{study}", response_model=Study)
    def get(
        study: str,
        access: Access = Depends(authorize("study", "get")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(study, repo, access), Study, collection=_COLLECTION
        )

    @router.patch("/{study}", response_model=Study)
    def patch(
        study: str,
        body: StudyUpdate,
        access: Access = Depends(authorize("study", "patch")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(study, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(repo.save(entity), Study, collection=_COLLECTION)

    @router.delete("/{study}", status_code=204)
    def delete(
        study: str,
        access: Access = Depends(authorize("study", "delete")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> None:
        _fetch(study, repo, access)
        repo.archive(study)
        return None

    @router.post("/{study}:undelete", response_model=Study)
    def undelete(
        study: str,
        access: Access = Depends(authorize("study", "undelete")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(study, repo, access)
        repo.unarchive(study)
        return serialize_one(entity, Study, collection=_COLLECTION)

    @router.post("/{study}:purge", status_code=204)
    def purge(
        study: str,
        access: Access = Depends(authorize("study", "purge")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> None:
        _fetch(study, repo, access)
        repo.delete(study)
        return None

    @router.get("", response_model=StudyList)
    def list_items(
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("study", "list")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> Any:
        items = access.scope_list(repo.list_all())
        window, next_token = paginate(items, params)
        rows = serialize_many(window, Study, collection=_COLLECTION)
        return {"studies": rows, "nextPageToken": next_token}

    @router.post(":lookup", response_model=Study)
    def lookup(
        body: StudyLookup,
        access: Access = Depends(authorize("study", "get")),
        repo: StudyRepository = Depends(repo_dep),
    ) -> Any:
        entity = repo.get_by_name(body.name)
        if entity is None:
            not_found(_COLLECTION, body.name)
        # The denial must match the not_found above byte for byte, or :lookup
        # tells a caller which studies exist outside their scope.
        return serialize_one(
            access.check_record(entity, name=body.name),
            Study,
            collection=_COLLECTION,
        )

    _ = (create, get, patch, delete, undelete, purge, list_items, lookup)
    return router
