"""Scheduler composition root.

Subclasses :class:`BaseContainer` (which already wires the entity and
repository graphs) and adds a ``use_cases`` sub-container holding the
interactors the Celery tasks invoke. The use-case providers are wired with
the concrete repository adapters resolved from the inherited
``repositories`` container — this is the one place where the abstract ports
get bound to real Couchbase/Mongo implementations.
"""

from openwellness_core.infrastructure.containers import BaseContainer
from openwellness_core.infrastructure.containers.providers import (
    DeclarativeContainer,
    DIContainer,
    DIDependenciesContainer,
    DIFactory,
)

from .application.use_cases.count_study_participants import (
    CountStudyParticipantsUseCase,
)


class UseCaseContainer(DeclarativeContainer):
    """Interactor providers, fed by the repository sub-container."""

    repositories = DIDependenciesContainer()

    count_study_participants = DIFactory(
        CountStudyParticipantsUseCase,
        participants=repositories.participant,
    )


class SchedulerContainer(BaseContainer):
    """Scheduler composition root; bound to a concrete ``AppConfig`` at boot."""

    use_cases = DIContainer(
        UseCaseContainer,
        repositories=BaseContainer.repositories,
    )
