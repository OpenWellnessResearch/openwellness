"""UserSleep resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import UserSleepRepository
from openwellness_core.domain.models.user_sleep import UserSleep as UserSleepEntity

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
from ..schemas.user_sleep import (
    UserSleep,
    UserSleepCreate,
    UserSleepList,
    UserSleepUpdate,
)

_COLLECTION = "userSleeps"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("user_sleep")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=UserSleep)
    def create(
        user: str,
        body: UserSleepCreate,
        access: Access = Depends(authorize("user_sleep", "create")),
        repo: UserSleepRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(UserSleepEntity(**payload)),
            UserSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{user_sleep}", response_model=UserSleep)
    def get(
        user: str,
        user_sleep: str,
        access: Access = Depends(authorize("user_sleep", "get")),
        repo: UserSleepRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, user_sleep, repo, access),
            UserSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{user_sleep}", response_model=UserSleep)
    def patch(
        user: str,
        user_sleep: str,
        body: UserSleepUpdate,
        access: Access = Depends(authorize("user_sleep", "patch")),
        repo: UserSleepRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, user_sleep, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            UserSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{user_sleep}", status_code=204)
    def delete(
        user: str,
        user_sleep: str,
        access: Access = Depends(authorize("user_sleep", "delete")),
        repo: UserSleepRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, user_sleep, repo, access)
        repo.archive(user_sleep)
        return None

    @router.post("/{user_sleep}:undelete", response_model=UserSleep)
    def undelete(
        user: str,
        user_sleep: str,
        access: Access = Depends(authorize("user_sleep", "undelete")),
        repo: UserSleepRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, user_sleep, repo, access)
        repo.unarchive(user_sleep)
        return serialize_one(
            entity,
            UserSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{user_sleep}:purge", status_code=204)
    def purge(
        user: str,
        user_sleep: str,
        access: Access = Depends(authorize("user_sleep", "purge")),
        repo: UserSleepRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, user_sleep, repo, access)
        repo.delete(user_sleep)
        return None

    @router.get("", response_model=UserSleepList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("user_sleep", "list")),
        repo: UserSleepRepository = Depends(repo_dep),
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
        items = access.scope_list(repo.get_for_owner_between(user, rng.start, rng.end))
        window, next_token = paginate(items, params)
        rows = serialize_many(
            window,
            UserSleep,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"userSleeps": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
