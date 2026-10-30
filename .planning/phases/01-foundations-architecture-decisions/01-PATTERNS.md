# Phase 1: Foundations & Architecture Decisions - Pattern Map

**Mapped:** 2026-10-29
**Files analyzed:** 13 (new/modified groups)
**Analogs found:** 9 / 13

All analog paths below were verified present in the repo (tracked source).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `.github/workflows/ci.yml` | config | batch | none (no `.github/`); wraps `backend/core/scripts/check_no_fstring_n1ql.py`, `backend/pyrightconfig.json` | none |
| `backend/core/src/openwellness_core/infrastructure/config/` (move Couchbase/SyncGateway/Mongo/Redis settings, add env_file resolution) | config | request-response | `backend/api/src/openwellness_api/config.py` lines 1-60 | exact (move) |
| `backend/api/src/openwellness_api/config.py`, `backend/scheduler/src/openwellness_scheduler/config.py` (modify: import from core) | config | - | itself | exact |
| `.env.example` (modify, document) | config | - | existing root `.env.example`, `docker-compose.yml` `env_file: .env` | exact |
| `backend/core/src/openwellness_core/domain/models/participant.py` (modify: ObjectId -> str) | model | CRUD | other str-id domain models (`domain/models/base_entity.py`) | role-match |
| mongo/cb participant model (`adapters/*/model/`) mapping str<->ObjectId in `from_domain`/`to_domain` | model | transform | `adapters/mongo/model/mongo_user.py` | role-match |
| `backend/api/src/openwellness_api/resources/participant.py` (drop `bson` import) | route | CRUD | `resources/weight.py` (canonical skeleton) | role-match |
| `core/application/repositories/user_repository.py` (add `get_by_email`) | port | CRUD | same file; implement in `adapters/mongo/repositories/mongo_user_repository.py` | exact |
| `core/application/repositories/refresh_session_repository.py` (new) + Mongo impl + export in `__init__.py` | port + adapter | CRUD (CAS rotate) | port style: `user_repository.py`; logic to move: `api/.../auth/session_store.py` | role-match |
| `api/.../auth/session_store.py`, `auth/service.py` (remove `pymongo` imports) | service | request-response | itself | exact |
| `core/.../containers/repository_container.py` (wire new repos) | config | DI | itself | exact |
| `mongo_base_repository.py` (FOUND-06) + `api/.../errors/handlers.py` | adapter / middleware | request-response | handlers.py `RedisError` handler | exact |
| `docs/adr/NNNN-*.md` (new dir, ~7 ADRs) | docs | - | none | none |

## Pattern Assignments

### Settings move to core (FOUND-02/03, D-17/D-18)

**Analog:** `backend/api/src/openwellness_api/config.py` lines 14-60 (move verbatim into `core/infrastructure/config/`):
```python
class MongoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONGO_", extra="ignore")
    url: str = "mongodb://localhost:27017"
    db: str = "openwellness"
    def get_url(self) -> str:
        return self.url
```
`AppConfig(AppConfigInterface)` composes them in `__init__` and exposes properties (lines 45-62). Services keep `API_`, `SMTP_`, `CELERY_` settings; Redis goes to core.

Add to the shared model_config (none sets `env_file` today). Suggested shared base in core:
```python
SettingsConfigDict(env_prefix=..., extra="ignore", env_file=_resolve_env_file())
```
where `_resolve_env_file()` returns `os.environ.get("OPENWELLNESS_ENV_FILE")` else repo root `.env` located by walking parents of `__file__` for `docker-compose.yml`. pydantic-settings default precedence (env > .env > defaults) already satisfies D-18. Under compose `env_file: .env` (docker-compose.yml lines 6, 21) injects real env, so behaviour is identical.

### Participant ObjectId removal (FOUND-04)

**Analog:** `domain/models/participant.py` lines 1-30 currently imports `bson.objectid.ObjectId` and uses `Optional[ObjectId]` for `assigned_coach_id`, `user_id`, `study_id` (`field(default_factory=ObjectId)`). Change to `Optional[str] = None` / `study_id: str = ""`. Convert in `adapters/mongo/model/*participant*` `from_domain`/`to_domain` (persistence models own ObjectId, per CLAUDE.md Entities pattern). Then fix `resources/participant.py` (hand-rolled, imports `bson`) to treat these as strings. Grep whole `domain/` and `application/` for `bson` after.

### get_by_email and RefreshSessionRepository ports (FOUND-05)

**Port style** (`application/repositories/user_repository.py` lines 1-14):
```python
class UserRepository(BaseCrudRepository[SomeUser, dict], Generic[SomeUser]):
    """Interface for the User repository."""
```
Add abstract `get_by_email(self, email: str) -> SomeUser | None`; implement in `mongo_user_repository.py` (and Couchbase user repo if one exists). New `RefreshSessionRepository` port exports in `repositories/__init__.py` (alphabetical imports, lines 3-30).

**Logic to relocate** from `api/auth/session_store.py`: single-use CAS rotation, family revoke on reuse, `_as_utc` coercion, exceptions `RefreshInvalid` / `RefreshReuse` (move to application exceptions), `RotationResult` frozen dataclass, injected `clock: Callable[[], datetime]`, no env reads. Keep the module-docstring invariants. Port methods take the sha256 hash only. API `AuthService` then depends on the port; remove `from pymongo.errors import DuplicateKeyError` (service.py line 35) and `OperationFailure` (session_store.py) by having the adapter raise a core duplicate/conflict exception. Existing tests `api/tests/test_session_store.py`, `test_auth_service.py`, `test_auth_container.py` are the regression net (mongomock).

### Honest repository errors (FOUND-06)

**Bad pattern to replace** (`mongo_base_repository.py` lines ~58-68):
```python
def get_by_id(self, entity_id: str):
    try:
        ... find_one({"_id": ObjectId(entity_id)})
    except AttributeError as e:
        print(...); return None
    except Exception as e:
        print(traceback.format_exc()); return None
```
Replace: catch `bson.errors.InvalidId` -> raise/return `EntityNotFoundException` path (404; or return None, which the router turns into `not_found`); let `pymongo.errors.PyMongoError` propagate (or wrap in a core `AdapterException`, already used at line ~49) and `logger.exception(...)`. Apply same in `save`/`delete` (`ObjectId(entity.id)` unguarded). Per D-11 the validation is version-agnostic UUID for Postgres later; keep ObjectId check inside the Mongo adapter only.

**API mapping analog** (`errors/handlers.py` lines 39-45 and 84-101): 404 via `build_error(404, "NOT_FOUND", ...)`; outage handler logs by type and returns 503:
```python
@app.exception_handler(RedisError)
async def _redis_unavailable(_: Request, exc: RedisError) -> JSONResponse:
    logger.error("Redis unavailable: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content=build_error(503, "UNAVAILABLE", "..."))
```
Add an equivalent handler for the core adapter-unavailable exception (type-only log, lazy `%s`). Test analog: `api/tests/test_error_mapping.py`.

### CI workflow (FOUND-01, D-15/D-16)

No analog. Commands to wrap (from CLAUDE.md): backend `uv sync --frozen` then `uv run pytest` in `backend/{core,api,scheduler}`, `uv run pyright` (config `backend/pyrightconfig.json`; errors fail, warnings do not, which is pyright's default exit behavior), `python backend/core/scripts/check_no_fstring_n1ql.py`; dashboard (`frontend/dashboard`, Node 22) `npm ci`, `npm run lint`, `npx tsc -b`, `npm test` (vitest run), `npm run format:check`; mobile (`frontend/mobile`) `./gradlew` JVM/Android host unit tests on ubuntu (e.g. `testDebugUnitTest`/`jvmTest`; confirm task names). iOS simulator job under `schedule`/`workflow_dispatch` only. Verify dashboard script names in `package.json` before planning.

### ADRs (FOUND-07, D-14)

No analog (`docs/` does not exist). Create `docs/adr/` with short MADR files (Context / Decision / Consequences): ids (D-11), timestamps (D-12), soft delete/purge (D-07..D-10), token format (D-13), owner semantics (D-01, must be confirmed from code first), authorization policy table (D-06; one row per entry in `resources/__init__.py` `RESOURCE_MODULES`, columns anon / participant-self / coach-in-study / admin by get/list/create/patch/delete/undelete/purge; denials per D-05), coach study claim (D-03, `roles.coach.studies`).

Owner evidence sources: `api/tests/test_weights_owner_crud.py`, `resources/weight.py` (owner-scoped reference), `common/handlers.py`, `auth/service.py` `_participant_pid` (line ~153) vs user id, `adapters/*/repositories/*owner*`. Roles-dict shape to extend: `service.py` `_roles_list` / `_participant_pid`. Timestamp conversions: `api/common/timestamps.py`.

## Shared Patterns

- **Module docstrings stating invariants; `from __future__ import annotations`; `logger = logging.getLogger(__name__)`; lazy `%s` logging; no `print`.**
- **Ports exported via `__init__.py`; adapters `mongo_*` / `cb_*`; wired only in `infrastructure/containers/repository_container.py`** (add new repo `DIFactory` entries there).
- **Error bodies via `build_error(...)`; routers never catch domain exceptions.**
- **Tests on fakes** (mongomock, fakeredis, `api/tests/conftest.py`) so CI needs no live services.

## No Analog Found

| File | Reason |
|---|---|
| `.github/workflows/*` | No existing CI |
| `docs/adr/*` | No docs dir |
| env-file resolution helper | No existing `env_file` use |

## Metadata

**Search scope:** `backend/{api,core,scheduler}`, `docker-compose.yml`, `.planning`
**Not verified:** exact Mongo participant model filename, scheduler config contents, dashboard/mobile script names, Couchbase user repo existence.
