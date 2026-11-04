"""Admin resource schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..common.pagination import list_response_model
from ._base import SCHEMA_CONFIG, ResourceBase


class AdminUserBody(BaseModel):
    """Nested user payload accepted in create/update bodies."""

    # from_attributes: responses carry the stored AdminUser dataclass, which
    # _entity_to_dict leaves nested, so validation must read it by attribute.
    model_config = SCHEMA_CONFIG | ConfigDict(from_attributes=True)

    id: str
    name: str = ""
    location: str = ""


class Admin(ResourceBase):
    """Admin resource.

    The domain's ``name`` is a dict (admin name parts) and lands on the
    wire as ``displayName``; the AIP ``name`` is the resource path.
    """

    display_name: dict = {}
    user: AdminUserBody | None = None
    groups: dict = {}
    study_ids: list[Any] = []
    time_created: datetime | None = None


class AdminCreate(BaseModel):
    """Body for ``POST /v1/admins``."""

    model_config = SCHEMA_CONFIG

    name: dict
    user: AdminUserBody | None = None
    groups: dict = {}
    study_ids: list[Any] = []


class AdminUpdate(BaseModel):
    """Body for ``PATCH /v1/admins/{admin}``."""

    model_config = SCHEMA_CONFIG

    name: dict | None = None
    user: AdminUserBody | None = None
    groups: dict | None = None
    study_ids: list[Any] | None = None


AdminList = list_response_model("admins", Admin)
