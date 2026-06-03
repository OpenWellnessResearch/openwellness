"""Celery task adapters.

These are *interface adapters*: each task converts a framework-level trigger
(Celery message args) into a use-case request, delegates to the interactor
resolved from the container, and converts the use-case response back into a
JSON-serializable payload Celery can put on the result backend.

No business rules live here — the task is deliberately thin. All the logic
sits in :mod:`...application.use_cases`, which can be tested without Celery.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from celery import shared_task

from ..application.use_cases.count_study_participants import (
    CountStudyParticipantsRequest,
)
from .celery_app import get_container


@shared_task(name="openwellness.count_study_participants")
def count_study_participants(study_id: str) -> dict[str, Any]:
    """Count total/active participants for ``study_id``.

    Resolves the interactor (with its concrete repository wired in) from the
    process container, runs it, and returns a plain dict for the result
    backend.
    """
    use_case = get_container().use_cases.count_study_participants()
    response = use_case.execute(CountStudyParticipantsRequest(study_id=study_id))
    return asdict(response)
