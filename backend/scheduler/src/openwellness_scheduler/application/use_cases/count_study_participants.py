"""Sample interactor: count the participants enrolled in a study.

This is the *use case* ring of Clean Architecture. It:

* depends only on the :class:`ParticipantRepository` **port** (an
  abstraction owned by the inner ``openwellness_core.application`` ring),
  never on a concrete Couchbase/Mongo adapter;
* receives its dependency by constructor injection, so the direction of
  source-code dependencies points inward (Dependency Inversion);
* crosses its boundaries with plain, framework-free data structures
  (the request/response dataclasses below) rather than ORM rows, HTTP
  objects, or Celery primitives.

Because of that, the interactor is exercised in tests with an in-memory
fake repository and no Celery, broker, or database in sight.
"""

from __future__ import annotations

from dataclasses import dataclass

from openwellness_core.application.repositories import ParticipantRepository


@dataclass(frozen=True)
class CountStudyParticipantsRequest:
    """Input data structure crossing the use-case boundary."""

    study_id: str


@dataclass(frozen=True)
class CountStudyParticipantsResponse:
    """Output data structure crossing the use-case boundary."""

    study_id: str
    total: int
    active: int


class CountStudyParticipantsUseCase:
    """Tally total and active participants for a single study."""

    def __init__(self, participants: ParticipantRepository) -> None:
        self._participants = participants

    def execute(
        self, request: CountStudyParticipantsRequest
    ) -> CountStudyParticipantsResponse:
        roster = self._participants.get_by_study_id(request.study_id)
        active = sum(1 for p in roster if getattr(p, "is_active", False))
        return CountStudyParticipantsResponse(
            study_id=request.study_id,
            total=len(roster),
            active=active,
        )
