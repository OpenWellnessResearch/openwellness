"""User resource — top-level."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from openwellness_core.application.repositories import UserRepository
from openwellness_core.domain.models.user import User as UserEntity

from ..authz.engine import Access, authorize
from ..common.handlers import (
    apply_patch,
    not_found,
    serialize_many,
    serialize_one,
)
from ..common.pagination import PageParams, page_params, paginate
from ..deps.container import container_dep
from ..schemas.user import (
    User,
    UserCreate,
    UserList,
    UserUpdate,
)

_COLLECTION = "users"


def build_router() -> APIRouter:
    router = APIRouter(prefix=f"/{_COLLECTION}", tags=[_COLLECTION])
    repo_dep = container_dep("user")

    def _fetch(id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_)
        return access.check_record(entity)

    @router.post("", status_code=201, response_model=User)
    def create(
        body: UserCreate,
        access: Access = Depends(authorize("user", "create")),
        repo: UserRepository = Depends(repo_dep),
    ) -> Any:
        payload = body.model_dump(exclude_unset=False)
        return serialize_one(
            repo.create(UserEntity(**payload)),
            User,
            collection=_COLLECTION,
        )

    @router.get("/{user}", response_model=User)
    def get(
        user: str,
        access: Access = Depends(authorize("user", "get")),
        repo: UserRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, repo, access), User, collection=_COLLECTION
        )

    @router.patch("/{user}", response_model=User)
    def patch(
        user: str,
        body: UserUpdate,
        access: Access = Depends(authorize("user", "patch")),
        repo: UserRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity), User, collection=_COLLECTION
        )

    @router.delete("/{user}", status_code=204)
    def delete(
        user: str,
        access: Access = Depends(authorize("user", "delete")),
        repo: UserRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, repo, access)
        repo.archive(user)
        return None

    @router.post("/{user}:undelete", response_model=User)
    def undelete(
        user: str,
        access: Access = Depends(authorize("user", "undelete")),
        repo: UserRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, repo, access)
        repo.unarchive(user)
        return serialize_one(entity, User, collection=_COLLECTION)

    @router.post("/{user}:purge", status_code=204)
    def purge(
        user: str,
        access: Access = Depends(authorize("user", "purge")),
        repo: UserRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, repo, access)
        repo.delete(user)
        return None

    @router.get("", response_model=UserList)
    def list_items(
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("user", "list")),
        repo: UserRepository = Depends(repo_dep),
    ) -> Any:
        items = access.scope_list(repo.list_all())
        window, next_token = paginate(items, params)
        rows = serialize_many(window, User, collection=_COLLECTION)
        return {"users": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
