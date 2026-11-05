"""JobRule resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

import arrow
from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import JobRuleRepository
from openwellness_core.domain.models.job_rule import JobRule as JobRuleEntity

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
from ..schemas.job_rule import (
    JobRule,
    JobRuleCreate,
    JobRuleList,
    JobRuleUpdate,
)

_COLLECTION = "jobRules"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("job_rule")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=JobRule)
    def create(
        user: str,
        body: JobRuleCreate,
        access: Access = Depends(authorize("job_rule", "create")),
        repo: JobRuleRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(JobRuleEntity(**payload)),
            JobRule,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{job_rule}", response_model=JobRule)
    def get(
        user: str,
        job_rule: str,
        access: Access = Depends(authorize("job_rule", "get")),
        repo: JobRuleRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, job_rule, repo, access),
            JobRule,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{job_rule}", response_model=JobRule)
    def patch(
        user: str,
        job_rule: str,
        body: JobRuleUpdate,
        access: Access = Depends(authorize("job_rule", "patch")),
        repo: JobRuleRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, job_rule, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            JobRule,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{job_rule}", status_code=204)
    def delete(
        user: str,
        job_rule: str,
        access: Access = Depends(authorize("job_rule", "delete")),
        repo: JobRuleRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, job_rule, repo, access)
        repo.archive(job_rule)
        return None

    @router.post("/{job_rule}:undelete", response_model=JobRule)
    def undelete(
        user: str,
        job_rule: str,
        access: Access = Depends(authorize("job_rule", "undelete")),
        repo: JobRuleRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, job_rule, repo, access)
        repo.unarchive(job_rule)
        return serialize_one(
            entity,
            JobRule,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{job_rule}:purge", status_code=204)
    def purge(
        user: str,
        job_rule: str,
        access: Access = Depends(authorize("job_rule", "purge")),
        repo: JobRuleRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, job_rule, repo, access)
        repo.delete(job_rule)
        return None

    @router.get("", response_model=JobRuleList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("job_rule", "list")),
        repo: JobRuleRepository = Depends(repo_dep),
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
            JobRule,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"jobRules": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
