"""SharedGoalProgress resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import SharedGoalProgressRepository
from openwellness_core.domain.models.shared_goal_progress import SharedGoalProgress as SharedGoalProgressEntity

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
from ..common.time_range import parse_str, resolve_time_range
from ..deps.container import container_dep
from ..schemas.shared_goal_progress import (
    SharedGoalProgress,
    SharedGoalProgressCreate,
    SharedGoalProgressList,
    SharedGoalProgressUpdate,
)

_COLLECTION = "sharedGoalProgress"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("shared_goal_progress")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=SharedGoalProgress)
    def create(
        user: str,
        body: SharedGoalProgressCreate,
        access: Access = Depends(authorize("shared_goal_progress", "create")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(SharedGoalProgressEntity(**payload)),
            SharedGoalProgress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{shared_goal_progress}", response_model=SharedGoalProgress)
    def get(
        user: str,
        shared_goal_progress: str,
        access: Access = Depends(authorize("shared_goal_progress", "get")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, shared_goal_progress, repo, access),
            SharedGoalProgress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{shared_goal_progress}", response_model=SharedGoalProgress)
    def patch(
        user: str,
        shared_goal_progress: str,
        body: SharedGoalProgressUpdate,
        access: Access = Depends(authorize("shared_goal_progress", "patch")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, shared_goal_progress, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            SharedGoalProgress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{shared_goal_progress}", status_code=204)
    def delete(
        user: str,
        shared_goal_progress: str,
        access: Access = Depends(authorize("shared_goal_progress", "delete")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, shared_goal_progress, repo, access)
        repo.archive(shared_goal_progress)
        return None

    @router.post("/{shared_goal_progress}:undelete", response_model=SharedGoalProgress)
    def undelete(
        user: str,
        shared_goal_progress: str,
        access: Access = Depends(authorize("shared_goal_progress", "undelete")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, shared_goal_progress, repo, access)
        repo.unarchive(shared_goal_progress)
        return serialize_one(
            entity,
            SharedGoalProgress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{shared_goal_progress}:purge", status_code=204)
    def purge(
        user: str,
        shared_goal_progress: str,
        access: Access = Depends(authorize("shared_goal_progress", "purge")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, shared_goal_progress, repo, access)
        repo.delete(shared_goal_progress)
        return None

    @router.get("", response_model=SharedGoalProgressList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("shared_goal_progress", "list")),
        repo: SharedGoalProgressRepository = Depends(repo_dep),
    ) -> Any:
        rng = resolve_time_range(
            start_time,
            end_time,
            parser=parse_str,
            require=False,
            max_span_days=None,
            default_start="1970-01-01",
            default_end="2100-01-01",
        )
        items = access.scope_list(
            repo.get_for_owner_between(user, rng.start, rng.end)
        )
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            SharedGoalProgress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"sharedGoalProgress": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
