"""Use-case tests — pure, no Celery/broker/database involved."""

from __future__ import annotations

from dataclasses import dataclass

from openwellness_scheduler.application.use_cases.count_study_participants import (
    CountStudyParticipantsRequest,
    CountStudyParticipantsUseCase,
)


@dataclass
class _StubParticipant:
    is_active: bool


def test_counts_total_and_active(fake_participants) -> None:
    fake_participants.add("study-1", _StubParticipant(is_active=True))
    fake_participants.add("study-1", _StubParticipant(is_active=False))
    fake_participants.add("study-1", _StubParticipant(is_active=True))
    # A participant in a different study must not leak into the tally.
    fake_participants.add("study-2", _StubParticipant(is_active=True))

    use_case = CountStudyParticipantsUseCase(participants=fake_participants)
    result = use_case.execute(CountStudyParticipantsRequest(study_id="study-1"))

    assert result.study_id == "study-1"
    assert result.total == 3
    assert result.active == 2


def test_unknown_study_is_zero(fake_participants) -> None:
    use_case = CountStudyParticipantsUseCase(participants=fake_participants)
    result = use_case.execute(CountStudyParticipantsRequest(study_id="nope"))

    assert result.total == 0
    assert result.active == 0
