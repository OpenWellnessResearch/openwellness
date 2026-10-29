<!-- refreshed: 2026-10-29 -->
# Architecture

**Analysis Date:** 2026-10-29

## System Overview

```text
┌──────────────────────────────┐          ┌──────────────────────────────┐
│ Dashboard (React SPA)        │          │ Mobile (Compose Multiplatform)│
│ `frontend/dashboard/src`     │          │ `frontend/mobile`             │
└───────────────┬──────────────┘          └───────────────┬──────────────┘
                │        HTTP · JSON · /v1 (AIP-style)    │
                └──────────────────┬──────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API service (FastAPI)  `backend/api/src/openwellness_api`               │
│  main.py · v1.py → resources/ (controllers) · auth/ · schemas/ · common/│
│  deps/ · errors/ · container.py (ApplicationContainer)                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  import openwellness_core
┌───────────────────────────────┴─────────────────────────────────────────┐
│ Scheduler (Celery)  `backend/scheduler/src/openwellness_scheduler`       │
│  infrastructure/tasks.py (thin adapters) → application/use_cases/        │
│  container.py (SchedulerContainer) · infrastructure/celery_app.py        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  import openwellness_core
┌───────────────────────────────┴─────────────────────────────────────────┐
│ Core library  `backend/core/src/openwellness_core`                       │
│  domain/ → application/ (ports) → adapters/ → infrastructure/           │
│  containers/ (BaseContainer DI root) · drivers/ · config/               │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
          Couchbase / Sync Gateway (N1QL)      MongoDB (pymongo)
          Redis: Celery broker + auth OTP/rate-limit store (`backend/api`)
```

## Pattern Overview

**Overall:** Clean Architecture (ports and adapters) in a Python uv workspace, with a shared `core` library consumed by two sibling services (`api`, `scheduler`) that do not import each other. The frontends are pure HTTP clients of the API.

**Key Characteristics:**
- Dependency rule enforced by convention and by tests: `domain/` imports nothing from the other layers; `application/` imports only `domain/`; `adapters/` and `infrastructure/` depend inward. Verified: no `openwellness_core.adapters` or `openwellness_core.infrastructure` imports exist under `core/src/openwellness_core/domain` or `core/src/openwellness_core/application`.
- Repository ports (`application/repositories/*.py`, ~41 modules) are the only persistence surface seen by use cases and API routes. Each port has a Couchbase implementation (`adapters/couchbase/repositories/`) or a Mongo implementation (`adapters/mongo/repositories/`).
- Composition is done with `dependency-injector` containers, not with module-level singletons. Services bind the concrete `AppConfig` by overriding `app_config`, and all routes/tasks resolve providers at call time so tests can override them.
- Entities are dataclasses (`core/src/openwellness_core/domain/models/`); persistence shapes are separate Pydantic classes in `adapters/*/model/` that map through `from_domain()` / `to_domain()`.
- The HTTP surface is Google AIP-style: `collection/{id}` resource names, standard methods plus `:undelete` / `:purge` custom verbs, and `/v1/auth:*` custom methods for OTP auth.

## Layers

**Domain (entities):**
- Purpose: Enterprise business data and invariants.
- Location: `backend/core/src/openwellness_core/domain/`
- Contains: `models/` (`BaseEntity`, `BaseOwnerEntity` and ~60 subclasses, including `models/actigraph/`, `models/condition/`), `value_objects/`, `exceptions/` (e.g. `weight_exceptions.py`, `goal_exceptions.py`).
- Depends on: Nothing from the other layers.
- Used by: `application/`, `adapters/`, `api/src/openwellness_api/resources/`, scheduler use cases.

**Application (use-case boundary / ports):**
- Purpose: Declares what the outside world may ask of persistence, and holds app-level DTOs.
- Location: `backend/core/src/openwellness_core/application/`
- Contains: `repositories/base_crud_repository.py` (generic CRUD port), `repositories/owner_crud_repository.py`, `repositories/fetchable_by_study_repository.py`, one port per entity (e.g. `repositories/weight_repository.py`, `repositories/participant_repository.py`), `dtos/activity_data_dto.py`, `exceptions.py`.
- Depends on: `domain/` only.
- Used by: `adapters/` (implements), `api/` resources (type-hints and resolves), `scheduler/` use cases (constructor-injected).

**Interface adapters (persistence implementations):**
- Purpose: Implement ports against a specific datastore and translate between domain entities and storage models.
- Location: `backend/core/src/openwellness_core/adapters/`
  - `couchbase/repositories/cb_*_repository.py` (~39 modules) and `couchbase/model/cb_*.py` (persistence classes with `from_domain`/`to_domain`).
  - `mongo/repositories/mongo_*_repository.py` (8 modules: admin, app, device, fitbit, participant, study, study_message, user) and `mongo/model/`.
  - `interfaces/` defines `CollectionRepository` / `MongoCollectionRepository` and result types (`insert_one_result.py`, `update_result.py`, ...), i.e. the low-level driver ports these adapters call.
  - `exceptions.py` holds adapter-level exceptions consumed by `api/src/openwellness_api/errors/handlers.py`.
- Depends on: `application/` ports, `domain/`, `infrastructure/drivers` via the `interfaces/` ports.
- Used by: Wired only by `infrastructure/containers/repository_container.py`.

**Infrastructure (frameworks and drivers, outermost in core):**
- Purpose: Concrete database clients, configuration slice, and DI composition root.
- Location: `backend/core/src/openwellness_core/infrastructure/`
  - `drivers/cb_entity_repository.py` (Sync Gateway HTTP + N1QL via Couchbase SDK, `CBEntityRepository`), `drivers/mdb_collection_repository.py` (pymongo wrapper, `MDBCollectionRepository`).
  - `config/app_config.py` (`AppConfigInterface`: Couchbase, Sync Gateway, Mongo keys).
  - `containers/base_container.py` (`BaseContainer`), `containers/entity_container.py`, `containers/repository_container.py` (one provider per repository), `containers/providers.py` (re-exports of `dependency_injector` primitives).
- Depends on: `interfaces/` ports, third-party drivers.
- Used by: Services subclass `BaseContainer`.

**API (interface adapter for HTTP):**
- Purpose: Controllers, wire schemas, auth, and error mapping. Contains no business rules (per `backend/api/README.md`).
- Location: `backend/api/src/openwellness_api/`
- Contains: `resources/` (one router module per entity, plus `RESOURCE_MODULES` list in `resources/__init__.py`), `schemas/` (Pydantic wire DTOs with camelCase aliasing via `schemas/_base.py`), `common/` (`handlers.py` serialize/patch/audit, `pagination.py`, `filter.py`, `time_range.py`, `resource_name.py`, `timestamps.py`), `deps/` (`container.py`, `principal.py`, `auth_container.py`), `errors/` (`handlers.py`, `responses.py`, `__init__.py`), `auth/` (OTP login, JWT, sessions).
- Depends on: `openwellness_core` (ports, entities, `BaseContainer`), FastAPI, Redis, SMTP.
- Used by: HTTP clients only.

**Scheduler (background interface adapter):**
- Purpose: Run scheduled and background jobs against the same datastores.
- Location: `backend/scheduler/src/openwellness_scheduler/`
- Contains: `application/use_cases/count_study_participants.py` (`CountStudyParticipantsUseCase`), `infrastructure/tasks.py` (Celery `shared_task` adapters, no business logic), `infrastructure/celery_app.py` (Celery app, worker init/shutdown signals, process-wide `get_container()`), `container.py` (`SchedulerContainer` with `UseCaseContainer`), `config.py` (`CelerySettings`, `AppConfig`).
- Depends on: `openwellness_core` ports only in use cases; Celery in infrastructure.
- Used by: Celery worker process (`celery -A openwellness_scheduler worker`).

**Frontend clients:**
- Dashboard: `frontend/dashboard/src/` organized as `app/` (router, providers, `routes.ts`), `pages/`, `features/auth/` (`api/`, `hooks/`, `model/`, `ui/`), `core/` (`api/apiClient.ts`, `auth/AuthContext.tsx`, `auth/RequireAuth.tsx`, `auth/tokenStorage.ts`, `ui/` primitives, `theme/`, `lib/`).
- Mobile: Compose Multiplatform modules `frontend/mobile/core/{domain,data,presentation}` and `frontend/mobile/feature/auth/{domain,data,presentation}`, plus `shared/` and `androidApp/`, `iosApp/` shells. Settings in `frontend/mobile/settings.gradle.kts`.

## Data Flow

### Primary Request Path (read of one entity, API)

1. Request enters FastAPI app built by `create_app()` in `backend/api/src/openwellness_api/main.py`; CORS and exception handlers are registered there.
2. `build_v1_router()` in `backend/api/src/openwellness_api/v1.py` mounts every `RESOURCE_MODULES` router under `/v1`.
3. Route function (e.g. `get_weight` in `backend/api/src/openwellness_api/resources/weight.py`) declares `repo: WeightRepository = Depends(container_dep("weight"))`.
4. `container_dep` in `backend/api/src/openwellness_api/deps/container.py` reads `request.app.state.container.repositories.weight` at request time.
5. The repository port method (`get_by_id`) executes in the adapter `CBWeightRepository` (`backend/core/src/openwellness_core/adapters/couchbase/repositories/cb_weight_repository.py`), which calls the `CBEntityRepository` driver.
6. Result is a domain `Weight` entity, converted by `serialize_one` in `backend/api/src/openwellness_api/common/handlers.py` into the Pydantic `Weight` wire schema (`backend/api/src/openwellness_api/schemas/weight.py`) with RFC-3339 timestamps and `name` resource names.
7. Domain exceptions raised anywhere on the path (e.g. `EntityNotFoundException`) are mapped by `backend/api/src/openwellness_api/errors/handlers.py` to AIP-193 error envelopes.

### Write Path (create, API)

1. `create_weight` (`resources/weight.py`) receives `WeightCreate` body and `Principal` from `get_principal` (`backend/api/src/openwellness_api/deps/principal.py`).
2. `stamp_audit` (`common/handlers.py`) adds owner and audit fields, then the domain entity is constructed (`WeightEntity(**payload)`).
3. `repo.create(entity)` persists through the port; response is serialized with status 201.

### Scheduled Job Path (scheduler)

1. Celery beat or a producer enqueues `openwellness.count_study_participants` (`backend/scheduler/src/openwellness_scheduler/infrastructure/tasks.py`).
2. The task calls `get_container().use_cases.count_study_participants()` (`infrastructure/celery_app.py` owns the process-wide container).
3. `CountStudyParticipantsUseCase.execute()` (`application/use_cases/count_study_participants.py`) uses only the `ParticipantRepository` port, injected via `UseCaseContainer` (`backend/scheduler/src/openwellness_scheduler/container.py`) from `repositories.participant`, which is the Mongo adapter `MongoParticipantRepository`.
4. The task returns `asdict(response)` to the Celery result backend (Redis).

### Authentication Flow (API)

1. `POST`-style custom methods `/v1/auth:sendLoginCode` and `/v1/auth:verifyLoginCode` are declared in `backend/api/src/openwellness_api/auth/router.py` (no router prefix, as required for `:verb` paths).
2. Each route resolves an `AuthService` via `auth_service_dep` (`backend/api/src/openwellness_api/deps/auth_container.py`), which assembles collaborators from `AuthContainer`.
3. `auth/service.py` orchestrates OTP generation and verification (`otp_store.py` on Redis), rate limits, email delivery (`email_sender.py`, SMTP), user lookup via the core `UserRepository` port, JWT issuance (`token_service.py`), and refresh sessions (`session_store.py` on Mongo).
4. The router maps service results to response schemas and never catches `LimitExceededException` (the global handler maps it to 429).

**State Management:**
- Server state is held in the datastores only. There is no in-process cache in the request path.
- Per-process objects: `ApplicationContainer` is stored on `app.state.container` (`main.py` lifespan), `AuthContainer` on `app.state.auth_container`. Scheduler uses a module-level `_container` in `celery_app.py`.
- Frontend auth tokens are managed by `frontend/dashboard/src/core/auth/tokenStorage.ts` and provided via `AuthContext.tsx`.

## Key Abstractions

**Repository port (`BaseCrudRepository` and specializations):**
- Purpose: Persistence contract per entity, free of storage detail.
- Examples: `backend/core/src/openwellness_core/application/repositories/base_crud_repository.py`, `owner_crud_repository.py`, `fetchable_by_study_repository.py`, `weight_repository.py`.
- Pattern: Abstract base class per entity; implemented by one Couchbase class and/or one Mongo class. Owner-scoped entities add `:undelete` via `unarchive` and soft-delete via `archive`, declared on the port (not on the entity).

**Base entities:**
- Purpose: Common identity, audit, and owner fields.
- Examples: `backend/core/src/openwellness_core/domain/models/base_entity.py`, `base_owner_entity.py`; Mongo/Couchbase bases in `adapters/mongo/model/mongo_base_entity.py`, `adapters/couchbase/model/cb_base_entity.py`.
- Pattern: Dataclass hierarchy in domain; Pydantic persistence hierarchy in adapters with `from_domain` / `to_domain`.

**Container providers (dependency-injector):**
- Purpose: Build and share repositories and use cases; allow test overrides.
- Examples: `backend/core/src/openwellness_core/infrastructure/containers/repository_container.py` (`DIFactory` per repo), `backend/scheduler/src/openwellness_scheduler/container.py` (`UseCaseContainer`).
- Pattern: Subclass `BaseContainer`, supply `app_config`, call `container.app_config.override(providers.Object(...))`.

**Resource router module:**
- Purpose: One FastAPI router per entity, with a canonical skeleton.
- Examples: `backend/api/src/openwellness_api/resources/weight.py` (owner-scoped reference), `resources/user.py` (top-level reference), `resources/participant.py` (hand-rolled for ObjectId fields).
- Pattern: `build_router()` returns an `APIRouter`; registered in `RESOURCE_MODULES` in `resources/__init__.py`.

**Use case interactor:**
- Purpose: Business operation with request/response dataclasses.
- Examples: `backend/scheduler/src/openwellness_scheduler/application/use_cases/count_study_participants.py`.
- Pattern: Constructor-injected port(s); `execute(request) -> response`; no Celery or DB imports.

## Entry Points

**API application:**
- Location: `backend/api/src/openwellness_api/main.py` (`app = create_app()`).
- Triggers: `uv run uvicorn openwellness_api.main:app` or the `api` container in `docker-compose.yml`.
- Responsibilities: Boot guard for auth secrets, open Couchbase, wire resource modules, start Redis client, register CORS, exception handlers, `/v1` router, `/healthz`.

**Scheduler worker:**
- Location: `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py` (`celery_app`).
- Triggers: `uv run celery -A openwellness_scheduler worker -l info`; beat via `beat_schedule` (currently commented out).
- Responsibilities: Configure broker and result backend, initialize Couchbase per worker process, register tasks from `infrastructure/tasks.py`.

**Dashboard SPA:**
- Location: `frontend/dashboard/src/app/App.tsx` (routing in `app/router.tsx`, paths in `app/routes.ts`).
- Triggers: `npm run dev` (Vite) on port 5173.

**Mobile app:**
- Location: `frontend/mobile/androidApp/src/main/kotlin/edu/openwellness/mobile/` and `frontend/mobile/iosApp/iosApp/`, shared UI in `frontend/mobile/shared/src/commonMain/`.

**Backend DI roots:**
- `backend/core/src/openwellness_core/infrastructure/containers/base_container.py` (`BaseContainer`), subclassed by `backend/api/src/openwellness_api/container.py` and `backend/scheduler/src/openwellness_scheduler/container.py`.

## Architectural Constraints

- **Threading:** The API declares sync `def` route handlers (e.g. `auth/router.py` notes they run in FastAPI's threadpool because `redis` and `smtplib` are synchronous). The Couchbase and Mongo clients are synchronous. The Celery worker runs tasks in its own process; `worker_process_init` opens the Couchbase connection per process.
- **Global state:** `backend/api/src/openwellness_api/main.py` builds `app` at import time. `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py` holds module-level `_container` and `celery_app`. `backend/api/src/openwellness_api/deps/auth_container.py` defines `AuthContainer` at module level.
- **Circular imports:** None observed between the three backend packages. `api` and `scheduler` depend only on `core`.
- **Core's dependency on drivers:** `core/src/openwellness_core/infrastructure/containers/repository_container.py` imports the concrete `adapters/couchbase` and `adapters/mongo` repositories directly, so the composition root is the one place where outer adapters are named. This is intentional.
- **Driver leakage into the API:** The API imports pymongo/bson types directly in a few places rather than going through core: `backend/api/src/openwellness_api/resources/participant.py` imports `bson.objectid.ObjectId`; `backend/api/src/openwellness_api/auth/service.py` and `auth/session_store.py` import `pymongo.errors`. This is an exception to the Dependency Rule as stated in `backend/core/README.md`.
- **Config leakage:** `backend/api/src/openwellness_api/config.py` and `backend/scheduler/src/openwellness_scheduler/config.py` import `AppConfigInterface` from `openwellness_core.infrastructure.config`, so services depend on a core infrastructure module (permitted: services are outer rings).

## Anti-Patterns

### Hand-rolled resource modules that diverge from the canonical skeleton

**What happens:** Most resource modules are generated from the `weight.py` skeleton, but `backend/api/src/openwellness_api/resources/participant.py` (and any module that handles `ObjectId`) hand-rolls its own serialization.
**Why it's wrong:** It duplicates `common/handlers.py` logic and carries a driver type (`bson.ObjectId`) into the HTTP layer, so changes to the standard handlers do not reach it.
**Do this instead:** Keep ObjectId-to-string conversion in `adapters/mongo/model/` (the `to_domain`/`from_domain` boundary) and reuse `serialize_one` / `serialize_many` from `backend/api/src/openwellness_api/common/handlers.py`.

### Per-service repository wiring leaking into the composition root

**What happens:** `backend/core/src/openwellness_core/infrastructure/containers/repository_container.py` documents per-adapter constructor quirks (`repo=`, `mongo_repo=`, `db=`, and hard-coded entity types). Some adapters accept `entity_type=` and others do not.
**Why it's wrong:** Adding a repository requires knowing which kwarg each adapter expects, and the port signature does not enforce a uniform constructor.
**Do this instead:** Give all adapters the same constructor shape (driver + `entity_type`) before adding new providers to `RepositoryContainer`.

### Mixed datastore access for a single entity family

**What happens:** The `participant` entity is served by Mongo (`MongoParticipantRepository`) for the API and the scheduler use case, while most other entities are on Couchbase. Both datastores are configured in every service.
**Why it's wrong:** Every service must start both clients and tests must fake both; the choice of store per entity is not recorded in one place.
**Do this instead:** When adding an entity, choose the store explicitly, implement the port in the matching `adapters/<store>/repositories/` subtree, and register it in `RepositoryContainer` next to its peers.

## Error Handling

**Strategy:** Domain and adapter code raise typed exceptions; the API maps them to HTTP responses centrally. Routers do not catch domain errors.

**Patterns:**
- Domain exceptions live in `backend/core/src/openwellness_core/domain/exceptions/` (e.g. `weight_exceptions.py`, `condition_exceptions.py`) and application exceptions in `backend/core/src/openwellness_core/application/exceptions.py`.
- `backend/api/src/openwellness_api/errors/handlers.py` registers handlers via `register_exception_handlers(app)`, producing the AIP-193 envelope from `errors/responses.py`.
- Auth raises `HTTPException` from `auth/service.py` for 400/401 and lets `LimitExceededException` propagate (429).
- Scheduler tasks let interactor exceptions propagate to Celery; `worker_process_init` logs and continues on initialization failure.

## Cross-Cutting Concerns

**Logging:** Standard `logging.getLogger(__name__)` in `backend/api/src/openwellness_api/main.py`, `auth/service.py`, and `infrastructure/celery_app.py`.
**Validation:** Pydantic v2 wire schemas in `backend/api/src/openwellness_api/schemas/` (`SCHEMA_CONFIG` in `schemas/_base.py`), domain validation in `domain/models/` and `domain/value_objects/`.
**Authentication:** Email OTP plus JWT access and refresh tokens (`backend/api/src/openwellness_api/auth/`). `deps/principal.py` resolves the caller: a valid bearer token yields an authenticated principal; otherwise the legacy `X-Principal-Id` header or `anonymous`. `require_principal` enforces when `API_AUTH_ENFORCE_PRINCIPAL` is set.
**Pagination and filtering:** Opaque cursor tokens (`backend/api/src/openwellness_api/common/pagination.py`) and the `filter=` subset (`common/filter.py`).

---

*Architecture analysis: 2026-10-29*
