"""Participant resource — study-scoped, hand-rolled for IntEnum flattening and
the ``studies/{study}`` parent."""

from __future__ import annotations

from dataclasses import fields as dc_fields
from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import ParticipantRepository
from openwellness_core.domain.models.participant import Participant as ParticipantEntity

from ..authz.engine import Access, authorize
from ..common.handlers import apply_patch, not_found
from ..common.pagination import PageParams, page_params, paginate
from ..common.resource_name import format_name
from ..common.timestamps import epoch_to_rfc3339
from ..deps.container import container_dep
from ..schemas.participant import (
    Participant,
    ParticipantCreate,
    ParticipantList,
    ParticipantUpdate,
)

_COLLECTION = "participants"
_PARENT = "studies"


def _parent_name(study: str) -> str:
    return format_name(collection=_PARENT, id_=study)


def _to_dict(p: ParticipantEntity) -> dict[str, Any]:
    """Hand-roll Participant serialization to flatten IntEnum."""
    out: dict[str, Any] = {}
    for f in dc_fields(p):
        v = getattr(p, f.name)
        if hasattr(v, "value") and hasattr(v, "name") and isinstance(v, int):
            v = int(v)
        out[f.name] = v
    return out


def _serialize(p: ParticipantEntity, study: str) -> dict[str, Any]:
    payload = _to_dict(p)
    payload["name"] = format_name(
        collection=_COLLECTION, id_=p.id, parent=_parent_name(study)
    )
    if "created_at" in payload:
        payload["createTime"] = epoch_to_rfc3339(payload.get("created_at"))
    if "updated_at" in payload:
        payload["updateTime"] = epoch_to_rfc3339(payload.get("updated_at"))
    for k in ("created_at", "updated_at", "created_at_tz_offset", "updated_at_tz_offset"):
        payload.pop(k, None)
    return Participant.model_validate(payload).model_dump(by_alias=True)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{study}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("participant")

    def _fetch(study: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(study))
        if entity.study_id != study:
            not_found(_COLLECTION, id_, parent=_parent_name(study))
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=Participant)
    def create(
        study: str,
        body: ParticipantCreate,
        access: Access = Depends(authorize("participant", "create")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        payload = body.model_dump(exclude_unset=False)
        payload["study_id"] = study
        return _serialize(repo.create(ParticipantEntity(**payload)), study)

    @router.get("/{participant}", response_model=Participant)
    def get(
        study: str,
        participant: str,
        access: Access = Depends(authorize("participant", "get")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        return _serialize(_fetch(study, participant, repo, access), study)

    @router.patch("/{participant}", response_model=Participant)
    def patch(
        study: str,
        participant: str,
        body: ParticipantUpdate,
        access: Access = Depends(authorize("participant", "patch")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(study, participant, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return _serialize(repo.save(entity), study)

    @router.delete("/{participant}", status_code=204)
    def delete(
        study: str,
        participant: str,
        access: Access = Depends(authorize("participant", "delete")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> None:
        _fetch(study, participant, repo, access)
        repo.archive(participant)
        return None

    @router.post("/{participant}:undelete", response_model=Participant)
    def undelete(
        study: str,
        participant: str,
        access: Access = Depends(authorize("participant", "undelete")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(study, participant, repo, access)
        repo.unarchive(participant)
        return _serialize(entity, study)

    @router.post("/{participant}:purge", status_code=204)
    def purge(
        study: str,
        participant: str,
        access: Access = Depends(authorize("participant", "purge")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> None:
        _fetch(study, participant, repo, access)
        repo.delete(participant)
        return None

    @router.get("", response_model=ParticipantList)
    def list_items(
        study: str,
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("participant", "list")),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        items = access.scope_list(repo.get_by_study_id(study))
        window, next_token = paginate(items, params)
        rows = [_serialize(p, study) for p in window]
        return {"participants": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
