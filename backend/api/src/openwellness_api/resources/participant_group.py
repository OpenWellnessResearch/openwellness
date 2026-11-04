"""ParticipantGroup resource — membership-scoped (users-parented).

Access is by membership (``participant_ids``) for a participant and by the
record's study for a coach, never by ``owner`` (ADR 0005, ADR 0007).
"""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import ParticipantGroupRepository
from openwellness_core.domain.models.participant_group import ParticipantGroup as ParticipantGroupEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..common.resource_name import format_name
from ..common.time_range import parse_arrow, resolve_time_range
from ..deps.container import container_dep
from ..schemas.participant_group import (
    ParticipantGroup,
    ParticipantGroupCreate,
    ParticipantGroupList,
    ParticipantGroupUpdate,
)

_COLLECTION = "participantGroups"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("participant_group")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        # No check_parent: the {user} segment is not an owner here.
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=ParticipantGroup)
    def create(
        user: str,
        body: ParticipantGroupCreate,
        access: Access = Depends(authorize("participant_group", "create")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        access.check_members(body.participant_ids)
        return serialize_one(
            repo.create(ParticipantGroupEntity(**payload)),
            ParticipantGroup,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{participant_group}", response_model=ParticipantGroup)
    def get(
        user: str,
        participant_group: str,
        access: Access = Depends(authorize("participant_group", "get")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, participant_group, repo, access),
            ParticipantGroup,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{participant_group}", response_model=ParticipantGroup)
    def patch(
        user: str,
        participant_group: str,
        body: ParticipantGroupUpdate,
        access: Access = Depends(authorize("participant_group", "patch")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, participant_group, repo, access)
        # Before apply_patch: the fetched entity may be the stored object.
        if body.participant_ids:
            access.check_members(body.participant_ids)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            ParticipantGroup,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{participant_group}", status_code=204)
    def delete(
        user: str,
        participant_group: str,
        access: Access = Depends(authorize("participant_group", "delete")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, participant_group, repo, access)
        repo.archive(participant_group)
        return None

    @router.post("/{participant_group}:undelete", response_model=ParticipantGroup)
    def undelete(
        user: str,
        participant_group: str,
        access: Access = Depends(authorize("participant_group", "undelete")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, participant_group, repo, access)
        repo.unarchive(participant_group)
        return serialize_one(
            entity,
            ParticipantGroup,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{participant_group}:purge", status_code=204)
    def purge(
        user: str,
        participant_group: str,
        access: Access = Depends(authorize("participant_group", "purge")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, participant_group, repo, access)
        repo.delete(participant_group)
        return None

    @router.get("", response_model=ParticipantGroupList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("participant_group", "list")),
        repo: ParticipantGroupRepository = Depends(repo_dep),
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
        # A-09-1: groups the {user} segment belongs to, for every caller. Scope runs
        # before the time window so an out-of-scope caller gets the D-08 404
        # whatever window they ask for.
        members = access.scope_list(
            [g for g in repo.list_all() if user in g.participant_ids]
        )
        lo, hi = rng.start.float_timestamp, rng.end.float_timestamp
        items = [g for g in members if lo <= g.created_at <= hi]
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            ParticipantGroup,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"participantGroups": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
