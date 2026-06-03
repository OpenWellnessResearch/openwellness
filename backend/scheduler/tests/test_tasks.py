"""Task-adapter tests.

Verify the container wiring (port → concrete provider override → use case)
and that the Celery task delegates to the interactor and returns a plain
serializable payload. The task runs in-process — no broker required.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from dependency_injector import providers

from openwellness_scheduler.container import SchedulerContainer
from openwellness_scheduler.infrastructure import celery_app as celery_app_module
from openwellness_scheduler.infrastructure.tasks import count_study_participants


@dataclass
class _StubParticipant:
    is_active: bool


@pytest.fixture
def wired_container(fake_participants):
    """A real container with the participant port overridden by the fake."""
    fake_participants.add("study-1", _StubParticipant(is_active=True))
    fake_participants.add("study-1", _StubParticipant(is_active=False))

    container = SchedulerContainer()
    container.repositories.participant.override(
        providers.Object(fake_participants)
    )

    original = celery_app_module.get_container()
    celery_app_module.set_container(container)
    try:
        yield container
    finally:
        celery_app_module.set_container(original)


def test_container_wires_use_case_with_overridden_repo(wired_container) -> None:
    use_case = wired_container.use_cases.count_study_participants()
    # The interactor must have received the *overridden* fake repository.
    assert use_case._participants is wired_container.repositories.participant()


def test_task_delegates_and_returns_dict(wired_container) -> None:
    result = count_study_participants("study-1")

    assert result == {"study_id": "study-1", "total": 2, "active": 1}
