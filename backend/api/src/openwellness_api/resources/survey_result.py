"""SurveyResult resource — owner-scoped (users-parented)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from openwellness_core.application.repositories import SurveyResultRepository
from openwellness_core.domain.models.survey_result import SurveyResult as SurveyResultEntity

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
from ..schemas.survey_result import (
    SurveyResult,
    SurveyResultCreate,
    SurveyResultList,
    SurveyResultUpdate,
)

_COLLECTION = "surveyResults"
_PARENT = "users"


def _parent_name(user: str) -> str:
    return format_name(collection=_PARENT, id_=user)


def build_router() -> APIRouter:
    router = APIRouter(
        prefix=f"/{_PARENT}/{{user}}/{_COLLECTION}", tags=[_COLLECTION]
    )
    repo_dep = container_dep("survey_result")

    def _fetch(user: str, id_: str, repo: Any, access: Access) -> Any:
        entity = repo.get_by_id(id_)
        if entity is None:
            not_found(_COLLECTION, id_, parent=_parent_name(user))
        return access.check_record(
            check_parent(
                entity, parent_id=user, collection=_COLLECTION, parent=_PARENT
            )
        )

    @router.post("", status_code=201, response_model=SurveyResult)
    def create(
        user: str,
        body: SurveyResultCreate,
        access: Access = Depends(authorize("survey_result", "create")),
        repo: SurveyResultRepository = Depends(repo_dep),
    ) -> Any:
        payload = access.stamp_create(
            body.model_dump(exclude_unset=False), parent_id=user
        )
        return serialize_one(
            repo.create(SurveyResultEntity(**payload)),
            SurveyResult,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.get("/{survey_result}", response_model=SurveyResult)
    def get(
        user: str,
        survey_result: str,
        access: Access = Depends(authorize("survey_result", "get")),
        repo: SurveyResultRepository = Depends(repo_dep),
    ) -> Any:
        return serialize_one(
            _fetch(user, survey_result, repo, access),
            SurveyResult,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.patch("/{survey_result}", response_model=SurveyResult)
    def patch(
        user: str,
        survey_result: str,
        body: SurveyResultUpdate,
        access: Access = Depends(authorize("survey_result", "patch")),
        repo: SurveyResultRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, survey_result, repo, access)
        apply_patch(entity, body, principal=access.principal)
        return serialize_one(
            repo.save(entity),
            SurveyResult,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.delete("/{survey_result}", status_code=204)
    def delete(
        user: str,
        survey_result: str,
        access: Access = Depends(authorize("survey_result", "delete")),
        repo: SurveyResultRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, survey_result, repo, access)
        repo.archive(survey_result)
        return None

    @router.post("/{survey_result}:undelete", response_model=SurveyResult)
    def undelete(
        user: str,
        survey_result: str,
        access: Access = Depends(authorize("survey_result", "undelete")),
        repo: SurveyResultRepository = Depends(repo_dep),
    ) -> Any:
        entity = _fetch(user, survey_result, repo, access)
        repo.unarchive(survey_result)
        return serialize_one(
            entity,
            SurveyResult,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )

    @router.post("/{survey_result}:purge", status_code=204)
    def purge(
        user: str,
        survey_result: str,
        access: Access = Depends(authorize("survey_result", "purge")),
        repo: SurveyResultRepository = Depends(repo_dep),
    ) -> None:
        _fetch(user, survey_result, repo, access)
        repo.delete(survey_result)
        return None

    @router.get("", response_model=SurveyResultList)
    def list_items(
        user: str,
        start_time: str | None = Query(default=None, alias="startTime"),
        end_time: str | None = Query(default=None, alias="endTime"),
        params: PageParams = Depends(page_params),
        access: Access = Depends(authorize("survey_result", "list")),
        repo: SurveyResultRepository = Depends(repo_dep),
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
            SurveyResult,
            collection=_COLLECTION,
            parent=_parent_name(user),
        )
        return {"surveyResults": rows, "nextPageToken": next_token}

    _ = (create, get, patch, delete, undelete, purge, list_items)
    return router
