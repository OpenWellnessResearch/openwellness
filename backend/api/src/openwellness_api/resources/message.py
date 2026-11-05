"""Message resource — owner-scoped, ``filter=`` supports ``subtype`` and ``condition``."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import MessageRepository
from openwellness_core.domain.models.message import Message as MessageEntity

from ..common.filter import parse_filter
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
from ..schemas.message import Message, MessageCreate, MessageList, MessageUpdate

_COLLECTION = "messages"
_PARENT = "users"
_FILTERABLE = {"subtype": int, "condition": int}


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("message")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=Message)
    def create(
        user: str,
        body: MessageCreate,
        access: Access = Depends(authorize("message", "create")),
        repo: MessageRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(MessageEntity(**payload)),
            Message,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{message}", response_model=Message)
    def get(
        user: str,
        message: str,
        access: Access = Depends(authorize("message", "get")),
        repo: MessageRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, message, repo, access),
            Message,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{message}", response_model=Message)
    def patch(
        user: str,
        message: str,
        body: MessageUpdate,
        access: Access = Depends(authorize("message", "patch")),
        repo: MessageRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, message, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            Message,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{message}", status_code=204)
    def delete(
        user: str,
        message: str,
        access: Access = Depends(authorize("message", "delete")),
        repo: MessageRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, message, repo, access)
        repo.archive(message)
        return None

    @router.post("/{message}:undelete", response_model=Message)
    def undelete(
        user: str,
        message: str,
        access: Access = Depends(authorize("message", "undelete")),
        repo: MessageRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, message, repo, access)
        repo.unarchive(message)
        return serialize_one(
            entity, Message, collection=_COLLECTION, parent=_parent_name(user)
        )

    @router.post("/{message}:purge", status_code=204)
    def purge(
        user: str,
        message: str,
        access: Access = Depends(authorize("message", "purge")),
        repo: MessageRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, message, repo, access)
        repo.delete(message)
        return None

    @router.get("", response_model=MessageList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        filter: str | None = Query(default=None),  # AIP-160
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("message", "list")),
        repo: MessageRepository = Depends(repo_dep),
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
        # Scope first (D-08): a coach's study filter runs on the unfiltered owner
        # list, so filter= can only narrow what the caller may already see.
        scoped = access.scope_list(
            repo.get_for_owner_between(user, rng.start, rng.end)
        )
        parsed = parse_filter(filter, allowed_fields=_FILTERABLE)
        if "subtype" in parsed or "condition" in parsed:
            # Intersect with the repository's own filter semantics.
            narrowed = repo.get_for_owner_between(
                user,
                rng.start,
                rng.end,
                subtype=parsed.get("subtype"),
                condition=parsed.get("condition"),
            )
            allowed = {m.id for m in scoped}
            results = [m for m in narrowed if m.id in allowed]
        else:
            results = scoped
        window, next_token = paginate(results, params)
        rows = serialize_many(
            window, Message, collection=_COLLECTION, parent=_parent_name(user)
        )
        return {"messages": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
