"""Participant resource — study-scoped, hand-rolled for IntEnum flattening and
the ``studies/{study}`` parent."""

from __future__ import annotations

from dataclasses import fields as dc_fields
from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import ParticipantRepository
from openwellness_core.domain.models.participant import Participant as ParticipantEntity

from ..common.handlers import (
    not_found,
    serialize_one as _serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..common.resource_name import format_name
from ..common.timestamps import epoch_to_rfc3339
from ..deps.container import container_dep
from ..deps.principal import Principal, get_principal
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

    def _fetch(study: str, id_: str, repo: Any) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(study))
        if entity.study_id != study:
            not_found(_COLLECTION, id_, parent=_parent_name(study))
        return entity

    @router.post("", status_code=201, response_model=Participant)
    def create(
        study: str,
        body: ParticipantCreate,
        principal: Principal = Depends(get_principal),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        payload = body.model_dump(exclude_unset=False)
        payload["study_id"] = study
        return _serialize(repo.create(ParticipantEntity(**payload)), study)

    @router.get("/{participant}", response_model=Participant)
    def get(
        study: str,
        participant: str,
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        return _serialize(_fetch(study, participant, repo), study)

    @router.patch("/{participant}", response_model=Participant)
    def patch(
        study: str,
        participant: str,
        body: ParticipantUpdate,
        principal: Principal = Depends(get_principal),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(study, participant, repo)
        data = body.model_dump(exclude_unset=True)
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return _serialize(repo.save(entity), study)

    @router.delete("/{participant}", status_code=204)
    def delete(
        study: str,
        participant: str,
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> None:
        _fetch(study, participant, repo)
        repo.archive(participant)
        return None

    @router.post("/{participant}:undelete", response_model=Participant)
    def undelete(
        study: str,
        participant: str,
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(study, participant, repo)
        repo.unarchive(participant)
        return _serialize(entity, study)

    @router.post("/{participant}:purge", status_code=204)
    def purge(
        study: str,
        participant: str,
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> None:
        _fetch(study, participant, repo)
        repo.delete(participant)
        return None

    @router.get("", response_model=ParticipantList)
    def list_items(
        study: str,
        params: PageParams = Depends(page_params),
        repo: ParticipantRepository = Depends(repo_dep),
    ) -> Any:
        items = repo.get_by_study_id(study)
        window, next_token = paginate(items, params)
        rows = [_serialize(p, study) for p in window]
        return {"participants": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
