"""Conversation resource — top-level with AIP-136 ``:search`` method."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import ConversationRepository
from openwellness_core.domain.models.conversation import Conversation as ConversationEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..deps.container import container_dep
from ..schemas.conversation import (
    Conversation,
    ConversationCreate,
    ConversationList,
    ConversationSearchBody,
    ConversationUpdate,
)

_COLLECTION = "conversations"


def build_router() -> APIRouter:
    router = APIRouter(prefix=f"/{_COLLECTION}", tags=[_COLLECTION])
    repo_dep = container_dep("conversation")

    def _fetch(id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_)
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=Conversation)
    def create(
        body: ConversationCreate,
        access: Access = Depends(authorize("conversation", "create")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> Any:
        # The body's owner stays; updated_by comes from the token (AUTH-06).
        entity = ConversationEntity(
            **access.stamp_create(body.model_dump(exclude_unset=False), parent_id=None)
        )
        return serialize_one(repo.create(entity), Conversation, collection=_COLLECTION)

    @router.get("/{conversation}", response_model=Conversation)
    def get(
        conversation: str,
        access: Access = Depends(authorize("conversation", "get")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(conversation, repo, access), Conversation, collection=_COLLECTION
        )

    @router.patch("/{conversation}", response_model=Conversation)
    def patch(
        conversation: str,
        body: ConversationUpdate,
        access: Access = Depends(authorize("conversation", "patch")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(conversation, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity), Conversation, collection=_COLLECTION
        )

    @router.delete("/{conversation}", status_code=204)
    def delete(
        conversation: str,
        access: Access = Depends(authorize("conversation", "delete")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> None:
        _fetch(conversation, repo, access)
        repo.archive(conversation)
        return None

    @router.post("/{conversation}:undelete", response_model=Conversation)
    def undelete(
        conversation: str,
        access: Access = Depends(authorize("conversation", "undelete")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(conversation, repo, access)
        repo.unarchive(conversation)
        return serialize_one(entity, Conversation, collection=_COLLECTION)

    @router.post("/{conversation}:purge", status_code=204)
    def purge(
        conversation: str,
        access: Access = Depends(authorize("conversation", "purge")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> None:
        _fetch(conversation, repo, access)
        repo.delete(conversation)
        return None

    @router.get("", response_model=ConversationList)
    def list_items(
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("conversation", "list")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> Any:
        items = access.scope_list(repo.list_all())
        window, next_token = paginate(items, params)
        rows = serialize_many(window, Conversation, collection=_COLLECTION)
        return {"conversations": rows, "nextPageToken": next_token}

    @router.post(":search", response_model=ConversationList)
    def search(
        body: ConversationSearchBody,
        params: PageParams = Depends(page_params),
        # A4: :search is op list, so the filter below cannot widen what a caller sees.
        access: Access = Depends(authorize("conversation", "list")),
        repo: ConversationRepository = Depends(repo_dep),
    ) -> Any:
        type_map = {
            "channels": ConversationEntity.Filter.Type.CHANNELS,
            "kind": ConversationEntity.Filter.Type.KIND,
            "week": ConversationEntity.Filter.Type.WEEK,
        }
        filters = [
            ConversationEntity.Filter(type=type_map[f.type], val=f.val)
            for f in body.filters
        ]
        results = access.scope_list(repo.get_for_filters(filters))
        window, next_token = paginate(results, params)
        rows = serialize_many(window, Conversation, collection=_COLLECTION)
        return {"conversations": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items, search)
    return router
