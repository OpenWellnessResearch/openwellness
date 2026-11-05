# Codebase Structure

**Analysis Date:** 2026-10-29

## Directory Layout

```
openwellness/                         # repo root
├── backend/                          # uv workspace (single lockfile, single venv)
│   ├── core/                         # openwellness-core: shared Clean Architecture library
│   │   ├── src/openwellness_core/
│   │   │   ├── domain/               # entities, value objects, domain exceptions
│   │   │   ├── application/          # repository ports, DTOs, app exceptions
│   │   │   ├── adapters/             # couchbase/ and mongo/ implementations, interfaces/
│   │   │   └── infrastructure/       # drivers/, config/, containers/ (DI root)
│   │   ├── scripts/                  # check_no_fstring_n1ql.py (N1QL lint helper)
│   │   └── tests/                    # core test suite (pytest)
│   ├── api/                          # openwellness-api: FastAPI service
│   │   ├── src/openwellness_api/     # main, v1, resources, schemas, auth, common, deps, errors
│   │   └── tests/                    # 18 test modules (pytest)
│   ├── scheduler/                    # openwellness-scheduler: Celery workers
│   │   ├── src/openwellness_scheduler/  # application/use_cases, infrastructure (celery, tasks)
│   │   └── tests/                    # pytest
│   ├── Dockerfile                    # multi-stage; targets `api` and `scheduler`
│   ├── .dockerignore
│   ├── README.md                     # backend overview and config table
│   └── (pyproject.toml, uv.lock, pyrightconfig.json at this level)
├── frontend/
│   ├── dashboard/                    # React SPA for coaches and admins (Vite, React 19, Tailwind v4)
│   │   ├── src/
│   │   │   ├── app/                  # App.tsx, router.tsx, routes.ts, providers.tsx
│   │   │   ├── pages/                # HomePage.tsx
│   │   │   ├── features/auth/        # api/, hooks/, model/, ui/
│   │   │   ├── core/                 # api/, auth/, ui/, theme/, lib/, errors.ts, result.ts
│   │   │   ├── styles/
│   │   │   └── test/                 # integration/, msw/ (MSW handlers)
│   │   └── public/
│   └── mobile/                       # Compose Multiplatform app (Android + iOS)
│       ├── androidApp/               # Android shell (src/main/kotlin, res/)
│       ├── iosApp/                   # Xcode project (iosApp.xcodeproj, Configuration/)
│       ├── shared/                   # KMP shared module (commonMain, androidMain, iosMain, tests)
│       ├── core/
│       │   ├── domain/               # shared domain utils
│       │   ├── data/                 # network/, auth/, di/ (per-platform actuals)
│       │   └── presentation/         # theme/, components/, util/, composeResources/
│       ├── feature/auth/
│       │   ├── domain/               # model/, usecase/
│       │   ├── data/                 # dto/, mapper/, di/
│       │   └── presentation/         # login/, register/, landing/, navigation/, di/, util/
│       ├── gradle/                   # wrapper and version catalog
│       ├── build.gradle.kts
│       └── settings.gradle.kts       # includes :androidApp, :shared, :core:*, :feature:auth:*
├── docker-compose.yml                # api, scheduler, redis; builds backend/Dockerfile
├── .env.example                      # shared env template (copy to backend/.env)
├── .gitignore
├── .planning/                        # GSD planning artifacts (this directory)
│   └── codebase/                     # codebase maps written by /gsd-map-codebase
├── README.md                         # system overview and quick start
├── CONTRIBUTING.md
├── LICENSE
└── NOTICE
```

## Directory Purposes

**`backend/core/src/openwellness_core/domain/`:**
- Purpose: Innermost ring. Entities as dataclasses and domain exceptions.
- Contains: `models/` (e.g. `weight.py`, `participant.py`, `goal.py`, `daily_state.py`, `actigraph/`, `condition/`), `value_objects/`, `exceptions/`.
- Key files: `models/base_entity.py`, `models/base_owner_entity.py`, `exceptions/domain_exception.py`.

**`backend/core/src/openwellness_core/application/`:**
- Purpose: Ports and use-case boundary types.
- Contains: `repositories/` (~41 port modules, exported from `repositories/__init__.py`), `dtos/`, `exceptions.py`.
- Key files: `repositories/base_crud_repository.py`, `repositories/owner_crud_repository.py`, `repositories/fetchable_by_study_repository.py`.

**`backend/core/src/openwellness_core/adapters/`:**
- Purpose: Datastore implementations of the ports.
- Contains:
  - `couchbase/model/` (`cb_*.py`, persistence classes), `couchbase/repositories/` (`cb_*_repository.py`, plus `_query_helpers.py` for N1QL parameterization).
  - `mongo/model/` (`mongo_*.py`), `mongo/repositories/` (`mongo_*_repository.py`, `mongo_base_repository.py`).
  - `interfaces/` (`collection_repository.py`, `mongo_collection_repository.py`, `entity_repository.py`, `results/`).
  - `exceptions.py`.

**`backend/core/src/openwellness_core/infrastructure/`:**
- Purpose: Drivers, configuration, and DI composition.
- Contains:
  - `drivers/cb_entity_repository.py` and `drivers/mdb_collection_repository.py`.
  - `config/app_config.py` (`AppConfigInterface`).
  - `containers/`: `base_container.py`, `entity_container.py`, `repository_container.py` (about 40 providers), `providers.py`.

**`backend/api/src/openwellness_api/`:**
- Purpose: HTTP service.
- Contains:
  - Top-level: `main.py` (app factory, lifespan, `app`), `v1.py` (router aggregator), `config.py` (`AppConfig`, `APISettings`), `container.py` (`ApplicationContainer`).
  - `resources/`: 40 entity router modules (e.g. `weight.py`, `user.py`, `participant.py`, `fitbit_sleep_session.py`, `user_stress.py`) and `__init__.py` listing `RESOURCE_MODULES`.
  - `schemas/`: 40 matching Pydantic wire modules plus `_base.py` (`SCHEMA_CONFIG`).
  - `auth/`: `router.py`, `service.py`, `schemas.py`, `token_service.py`, `otp_store.py`, `session_store.py`, `email_sender.py`, `errors.py`.
  - `common/`: `handlers.py`, `pagination.py`, `filter.py`, `time_range.py`, `resource_name.py`, `timestamps.py`.
  - `deps/`: `container.py`, `auth_container.py`, `principal.py`.
  - `errors/`: `handlers.py`, `responses.py`.

**`backend/scheduler/src/openwellness_scheduler/`:**
- Purpose: Background jobs.
- Contains: `container.py` (`SchedulerContainer`, `UseCaseContainer`), `config.py`, `application/use_cases/count_study_participants.py`, `infrastructure/celery_app.py`, `infrastructure/tasks.py`.

**`backend/api/tests/`, `backend/core/tests/`, `backend/scheduler/tests/`:**
- Purpose: Unit and contract tests using in-memory fakes; no live datastore needed.
- Contains: `conftest.py` per package, `test_*.py` modules. Examples: `backend/api/tests/test_users_crud.py`, `backend/api/tests/test_weights_owner_crud.py`, `backend/api/tests/test_auth_service.py`, `backend/scheduler/tests/test_tasks.py`.

**`frontend/dashboard/src/`:**
- Purpose: Coach and admin SPA.
- Contains: `app/` (composition), `pages/`, `features/<feature>/{api,hooks,model,ui}/` (only `auth` exists), `core/` (cross-feature infrastructure), `styles/`, `test/`.

**`frontend/mobile/`:**
- Purpose: Participant app (Compose Multiplatform).
- Contains: Feature modules follow `feature/<name>/{domain,data,presentation}`; cross-cutting modules under `core/`; platform shells `androidApp/` and `iosApp/`; `shared/` wires DI (`di/`) and home.

## Key File Locations

**Entry Points:**
- `backend/api/src/openwellness_api/main.py`: API app (`app`), lifespan, `/healthz`.
- `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`: Celery app (`celery_app`).
- `frontend/dashboard/src/app/App.tsx`: SPA root.
- `frontend/mobile/androidApp/src/main/kotlin/edu/openwellness/mobile/`: Android entry.
- `frontend/mobile/iosApp/iosApp/`: iOS entry.

**Configuration:**
- `backend/core/src/openwellness_core/infrastructure/config/app_config.py`: shared config interface.
- `backend/api/src/openwellness_api/config.py`: API settings (`API_*`, auth, SMTP, Redis).
- `backend/scheduler/src/openwellness_scheduler/config.py`: `CELERY_*` settings.
- `backend/pyrightconfig.json`: type-check config for the workspace.
- `.env.example` (repo root): environment template. Do not commit a real `.env`.
- `docker-compose.yml`: local stack definition.
- `frontend/dashboard/src/core/api/env.ts`: dashboard API base URL.
- `frontend/mobile/settings.gradle.kts`: Gradle module graph.

**Core Logic:**
- `backend/core/src/openwellness_core/domain/models/`: entity definitions.
- `backend/core/src/openwellness_core/application/repositories/`: persistence ports.
- `backend/core/src/openwellness_core/adapters/couchbase/repositories/` and `adapters/mongo/repositories/`: implementations.
- `backend/core/src/openwellness_core/infrastructure/containers/repository_container.py`: which store backs each entity.
- `backend/api/src/openwellness_api/resources/`: HTTP routes.
- `backend/api/src/openwellness_api/auth/`: OTP and JWT flow.
- `backend/scheduler/src/openwellness_scheduler/application/use_cases/`: background use cases.
- `frontend/dashboard/src/features/auth/`: dashboard login flow.

**Testing:**
- `backend/api/tests/conftest.py`, `backend/core/tests/`, `backend/scheduler/tests/conftest.py`.
- `frontend/dashboard/src/test/msw/` and `frontend/dashboard/src/test/integration/`.
- Co-located frontend tests: `*.test.ts` / `*.test.tsx` beside the source (e.g. `frontend/dashboard/src/features/auth/hooks/useLogin.test.tsx`).
- Mobile tests: `*/src/commonTest`, `*/src/androidHostTest`, `*/src/iosTest`.

## Naming Conventions

**Files (backend Python):**
- Snake_case modules. Entity-scoped modules use the entity name: `weight.py`, `fitbit_sleep_session.py`.
- Couchbase adapters: `cb_<entity>_repository.py` and `model/cb_<entity>.py`.
- Mongo adapters: `mongo_<entity>_repository.py` and `model/mongo_<entity>.py`.
- Ports: `<entity>_repository.py` in `application/repositories/`.
- Wire schemas: `schemas/<entity>.py`, matching `resources/<entity>.py`.

**Files (frontend):**
- Dashboard: React components in PascalCase (`EmailField.tsx`, `LoadingButton.tsx`, `RequireAuth.tsx`), non-component modules in camelCase (`apiClient.ts`, `tokenStorage.ts`), tests as `<name>.test.ts(x)` beside the source.
- Mobile: Kotlin files in PascalCase by class (`LoginViewModel`-style names under `presentation/login/`).

**Directories:**
- Python packages: snake_case under `src/openwellness_<pkg>/`.
- Layer directories are plural nouns for collections (`repositories/`, `resources/`, `schemas/`, `exceptions/`) and singular for concepts (`domain/`, `application/`, `adapters/`, `infrastructure/`, `auth/`, `common/`, `deps/`, `errors/`).
- Mobile packages follow `edu.openwellness.mobile.<module>.<layer>`.

## Where to Add New Code

**New entity (end-to-end):**
1. Domain model: `backend/core/src/openwellness_core/domain/models/<entity>.py` (subclass `BaseEntity` or `BaseOwnerEntity`).
2. Domain exceptions if needed: `backend/core/src/openwellness_core/domain/exceptions/<entity>_exceptions.py`.
3. Port: `backend/core/src/openwellness_core/application/repositories/<entity>_repository.py` and export from `application/repositories/__init__.py`.
4. Persistence model and adapter: `backend/core/src/openwellness_core/adapters/couchbase/model/cb_<entity>.py` and `adapters/couchbase/repositories/cb_<entity>_repository.py` (or the Mongo equivalents).
5. Provider: add an entity provider to `backend/core/src/openwellness_core/infrastructure/containers/entity_container.py` and a repository provider to `repository_container.py`.
6. Wire schema: `backend/api/src/openwellness_api/schemas/<entity>.py`.
7. Router: `backend/api/src/openwellness_api/resources/<entity>.py` with `build_router()`; add the module to `RESOURCE_MODULES` in `resources/__init__.py` (and to the import list at the top of that file).
8. Tests: `backend/api/tests/test_<entity>_crud.py` (pattern: `test_weights_owner_crud.py`) and `backend/core/tests/` for mapper round-trips.

**New API endpoint on an existing resource:**
- Add the route to `backend/api/src/openwellness_api/resources/<entity>.py` inside `build_router()`, use `Depends(container_dep("<provider>"))` for the repository, and put shared logic in `backend/api/src/openwellness_api/common/`.

**New auth or custom-method feature:**
- Router: `backend/api/src/openwellness_api/auth/router.py` pattern (no prefix, full `/<path>:<verb>`), or a new module under `backend/api/src/openwellness_api/` mounted in `v1.py`.

**New background job:**
- Use case: `backend/scheduler/src/openwellness_scheduler/application/use_cases/<job>.py` with request and response dataclasses.
- Container: add a `DIFactory` in `UseCaseContainer` (`backend/scheduler/src/openwellness_scheduler/container.py`).
- Task: thin adapter in `backend/scheduler/src/openwellness_scheduler/infrastructure/tasks.py` using `@shared_task(name="openwellness.<job>")`.
- Schedule: `beat_schedule` in `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`.

**New dashboard feature:**
- Create `frontend/dashboard/src/features/<name>/{api,hooks,model,ui}/`, mirroring `features/auth/`. Shared primitives go in `frontend/dashboard/src/core/ui/`; routes in `frontend/dashboard/src/app/routes.ts`.

**New mobile feature:**
- Create `frontend/mobile/feature/<name>/{domain,data,presentation}` modules, register them in `frontend/mobile/settings.gradle.kts`, and wire DI in `shared/src/commonMain/kotlin/edu/openwellness/mobile/di/`.

**Shared utilities:**
- Backend HTTP helpers: `backend/api/src/openwellness_api/common/`.
- Backend domain helpers: `backend/core/src/openwellness_core/domain/value_objects/`.
- Dashboard: `frontend/dashboard/src/core/lib/cn.ts` and `core/api/`.

## Special Directories

**`backend/core/src/openwellness_core/adapters/mongo/` and `.../couchbase/`:**
- Purpose: Datastore implementations.
- Generated: No.
- Committed: Yes.

**`.planning/`:**
- Purpose: GSD planning and codebase maps. `.planning/codebase/` holds these documents.
- Generated: Yes, by `/gsd-map-codebase` and other GSD commands.
- Committed: Per project policy (currently present in the working tree; not part of the runtime).

**`frontend/mobile/iosApp/iosApp.xcodeproj/`:**
- Purpose: Xcode project for the iOS shell.
- Generated: No (hand-maintained Xcode project).
- Committed: Yes.

**`frontend/mobile/gradle/wrapper/`:**
- Purpose: Gradle wrapper.
- Generated: Yes (by `gradle wrapper`).
- Committed: Yes.

**`backend/**/.venv`, `node_modules`, build outputs:**
- Created by `uv sync`, `npm install`, and Gradle builds. Excluded by `.gitignore`.
- Not committed.

---

*Structure analysis: 2026-10-29*
