# scheduler

Celery workers (and beat, if scheduled tasks are needed).

Depends on `../core`. Talks to the same database and shared code as `api/`,
not over HTTP.

## Layout (Clean Architecture)

Dependencies point inward only — outer rings know about inner rings, never
the reverse:

| Ring | Location | Responsibility |
| --- | --- | --- |
| Entities | `openwellness_core.domain` | Domain models (e.g. `Participant`). |
| Use cases | `application/use_cases/` | Interactors with the business rules. Depend only on repository **ports** from `openwellness_core.application`. No Celery/DB imports. |
| Interface adapters | `infrastructure/tasks.py` | Thin Celery tasks: translate message args ↔ use-case request/response. No business logic. |
| Frameworks & drivers | `infrastructure/celery_app.py`, `config.py`, `container.py` | Celery app, broker config, and the DI container that binds the abstract ports to concrete Couchbase/Mongo adapters. |

The sample interactor `CountStudyParticipantsUseCase` is wired with its
concrete `ParticipantRepository` by `SchedulerContainer`; the
`openwellness.count_study_participants` task just resolves and invokes it.

## Running

Set the broker/backend (defaults assume a local Redis):

```sh
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Start a worker:

```sh
celery -A openwellness_scheduler worker -l info
```

Enqueue the sample task:

```python
from openwellness_scheduler.infrastructure.tasks import count_study_participants
count_study_participants.delay("<study-object-id>")
```

For a periodic run, uncomment the `beat_schedule` entry in
`infrastructure/celery_app.py` and run `celery -A openwellness_scheduler beat`.
