"""Card resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import CardRepository
from openwellness_core.domain.models.card import Card as CardEntity

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
from ..schemas.card import (
    Card,
    CardCreate,
    CardList,
    CardUpdate,
)

_COLLECTION = "cards"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("card")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=Card)
    def create(
        user: str,
        body: CardCreate,
        access: Access = Depends(authorize("card", "create")),
        repo: CardRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(CardEntity(**payload)),
            Card,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{card}", response_model=Card)
    def get(
        user: str,
        card: str,
        access: Access = Depends(authorize("card", "get")),
        repo: CardRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, card, repo, access),
            Card,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{card}", response_model=Card)
    def patch(
        user: str,
        card: str,
        body: CardUpdate,
        access: Access = Depends(authorize("card", "patch")),
        repo: CardRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, card, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            Card,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{card}", status_code=204)
    def delete(
        user: str,
        card: str,
        access: Access = Depends(authorize("card", "delete")),
        repo: CardRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, card, repo, access)
        repo.archive(card)
        return None

    @router.post("/{card}:undelete", response_model=Card)
    def undelete(
        user: str,
        card: str,
        access: Access = Depends(authorize("card", "undelete")),
        repo: CardRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, card, repo, access)
        repo.unarchive(card)
        return serialize_one(
            entity,
            Card,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{card}:purge", status_code=204)
    def purge(
        user: str,
        card: str,
        access: Access = Depends(authorize("card", "purge")),
        repo: CardRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, card, repo, access)
        repo.delete(card)
        return None

    @router.get("", response_model=CardList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("card", "list")),
        repo: CardRepository = Depends(repo_dep),
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
        items = access.scope_list(repo.get_for_owner_between(user, rng.start, rng.end))
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            Card,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"cards": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
