"""MessageDraft resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import MessageDraftRepository
from openwellness_core.domain.models.message_draft import MessageDraft as MessageDraftEntity

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
from ..schemas.message_draft import (
    MessageDraft,
    MessageDraftCreate,
    MessageDraftList,
    MessageDraftUpdate,
)

_COLLECTION = "messageDrafts"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("message_draft")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=MessageDraft)
    def create(
        user: str,
        body: MessageDraftCreate,
        access: Access = Depends(authorize("message_draft", "create")),
        repo: MessageDraftRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(MessageDraftEntity(**payload)),
            MessageDraft,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{message_draft}", response_model=MessageDraft)
    def get(
        user: str,
        message_draft: str,
        access: Access = Depends(authorize("message_draft", "get")),
        repo: MessageDraftRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, message_draft, repo, access),
            MessageDraft,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{message_draft}", response_model=MessageDraft)
    def patch(
        user: str,
        message_draft: str,
        body: MessageDraftUpdate,
        access: Access = Depends(authorize("message_draft", "patch")),
        repo: MessageDraftRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, message_draft, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            MessageDraft,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{message_draft}", status_code=204)
    def delete(
        user: str,
        message_draft: str,
        access: Access = Depends(authorize("message_draft", "delete")),
        repo: MessageDraftRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, message_draft, repo, access)
        repo.archive(message_draft)
        return None

    @router.post("/{message_draft}:undelete", response_model=MessageDraft)
    def undelete(
        user: str,
        message_draft: str,
        access: Access = Depends(authorize("message_draft", "undelete")),
        repo: MessageDraftRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, message_draft, repo, access)
        repo.unarchive(message_draft)
        return serialize_one(
            entity,
            MessageDraft,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{message_draft}:purge", status_code=204)
    def purge(
        user: str,
        message_draft: str,
        access: Access = Depends(authorize("message_draft", "purge")),
        repo: MessageDraftRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, message_draft, repo, access)
        repo.delete(message_draft)
        return None

    @router.get("", response_model=MessageDraftList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("message_draft", "list")),
        repo: MessageDraftRepository = Depends(repo_dep),
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
        items = access.scope_list(
            repo.get_for_owner_between(user, rng.start, rng.end)
        )
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            MessageDraft,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"messageDrafts": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
