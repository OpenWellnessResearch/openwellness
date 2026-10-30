"""Participant resource schemas (study-scoped)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from ..common.pagination import list_response_model
from ._base import SCHEMA_CONFIG, ResourceBase


class Participant(ResourceBase):
    """Participant resource (study-scoped).

    ``study_id`` / ``assigned_coach_id`` / ``user_id`` are strings in the
    domain and on the wire; the Mongo adapter stores them as ``ObjectId``.
    """

    study_id: str = ""
    participant_number: str = ""
    is_active: bool = False
    assigned_coach_id: str | None = None
    user_id: str | None = None
    google_id: str | None = None
    device_id: str | None = None
    assessment_weight: float = 0.0
    start_weight: float = 0.0
    height_in_inches: float = 0.0
    participant_type: int = 0
    tz: str | None = None
    gender: int | None = None
    time_created: datetime | None = None


class ParticipantCreate(BaseModel):
    """Body for ``POST /v1/studies/{study}/participants``."""

    model_config = SCHEMA_CONFIG

    participant_number: str = ""
    is_active: bool = False
    assigned_coach_id: str | None = None
    user_id: str | None = None
    google_id: str | None = None
    device_id: str | None = None
    assessment_weight: float = 0.0
    start_weight: float = 0.0
    height_in_inches: float = 0.0
    participant_type: int = 0
    tz: str | None = None
    gender: int | None = None


class ParticipantUpdate(BaseModel):
    """Body for ``PATCH /v1/studies/{study}/participants/{participant}``."""

    model_config = SCHEMA_CONFIG

    participant_number: str | None = None
    is_active: bool | None = None
    assigned_coach_id: str | None = None
    user_id: str | None = None
    google_id: str | None = None
    device_id: str | None = None
    assessment_weight: float | None = None
    start_weight: float | None = None
    height_in_inches: float | None = None
    participant_type: int | None = None
    tz: str | None = None
    gender: int | None = None


ParticipantList = list_response_model("participants", Participant)
