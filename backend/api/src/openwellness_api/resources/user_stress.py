"""UserStress resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import UserStressRepository
from openwellness_core.domain.models.user_stress import UserStress as UserStressEntity

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
from ..schemas.user_stress import (
    UserStress,
    UserStressCreate,
    UserStressList,
    UserStressUpdate,
)

_COLLECTION = "userStresses"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("user_stress")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=UserStress)
    def create(
        user: str,
        body: UserStressCreate,
        access: Access = Depends(authorize("user_stress", "create")),
        repo: UserStressRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(UserStressEntity(**payload)),
            UserStress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{user_stress}", response_model=UserStress)
    def get(
        user: str,
        user_stress: str,
        access: Access = Depends(authorize("user_stress", "get")),
        repo: UserStressRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, user_stress, repo, access),
            UserStress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{user_stress}", response_model=UserStress)
    def patch(
        user: str,
        user_stress: str,
        body: UserStressUpdate,
        access: Access = Depends(authorize("user_stress", "patch")),
        repo: UserStressRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, user_stress, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            UserStress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{user_stress}", status_code=204)
    def delete(
        user: str,
        user_stress: str,
        access: Access = Depends(authorize("user_stress", "delete")),
        repo: UserStressRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, user_stress, repo, access)
        repo.archive(user_stress)
        return None

    @router.post("/{user_stress}:undelete", response_model=UserStress)
    def undelete(
        user: str,
        user_stress: str,
        access: Access = Depends(authorize("user_stress", "undelete")),
        repo: UserStressRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, user_stress, repo, access)
        repo.unarchive(user_stress)
        return serialize_one(
            entity,
            UserStress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{user_stress}:purge", status_code=204)
    def purge(
        user: str,
        user_stress: str,
        access: Access = Depends(authorize("user_stress", "purge")),
        repo: UserStressRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, user_stress, repo, access)
        repo.delete(user_stress)
        return None

    @router.get("", response_model=UserStressList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("user_stress", "list")),
        repo: UserStressRepository = Depends(repo_dep),
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
            UserStress,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"userStresses": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
