"""UserSettings resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import UserSettingsRepository
from openwellness_core.domain.models.user_settings import UserSettings as UserSettingsEntity

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
from ..schemas.user_settings import (
    UserSettings,
    UserSettingsCreate,
    UserSettingsList,
    UserSettingsUpdate,
)

_COLLECTION = "userSettings"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("user_settings")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=UserSettings)
    def create(
        user: str,
        body: UserSettingsCreate,
        access: Access = Depends(authorize("user_settings", "create")),
        repo: UserSettingsRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(UserSettingsEntity(**payload)),
            UserSettings,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{user_settings}", response_model=UserSettings)
    def get(
        user: str,
        user_settings: str,
        access: Access = Depends(authorize("user_settings", "get")),
        repo: UserSettingsRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, user_settings, repo, access),
            UserSettings,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{user_settings}", response_model=UserSettings)
    def patch(
        user: str,
        user_settings: str,
        body: UserSettingsUpdate,
        access: Access = Depends(authorize("user_settings", "patch")),
        repo: UserSettingsRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, user_settings, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            UserSettings,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{user_settings}", status_code=204)
    def delete(
        user: str,
        user_settings: str,
        access: Access = Depends(authorize("user_settings", "delete")),
        repo: UserSettingsRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, user_settings, repo, access)
        repo.archive(user_settings)
        return None

    @router.post("/{user_settings}:undelete", response_model=UserSettings)
    def undelete(
        user: str,
        user_settings: str,
        access: Access = Depends(authorize("user_settings", "undelete")),
        repo: UserSettingsRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, user_settings, repo, access)
        repo.unarchive(user_settings)
        return serialize_one(
            entity,
            UserSettings,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{user_settings}:purge", status_code=204)
    def purge(
        user: str,
        user_settings: str,
        access: Access = Depends(authorize("user_settings", "purge")),
        repo: UserSettingsRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, user_settings, repo, access)
        repo.delete(user_settings)
        return None

    @router.get("", response_model=UserSettingsList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("user_settings", "list")),
        repo: UserSettingsRepository = Depends(repo_dep),
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
            UserSettings,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"userSettings": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
