---
phase: 01-foundations-architecture-decisions
reviewed: 2026-10-30T00:00:00Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - .env.example
  - .github/workflows/ci.yml
  - .github/workflows/ios-nightly.yml
  - backend/api/src/openwellness_api/auth/service.py
  - backend/api/src/openwellness_api/auth/session_store.py
  - backend/api/src/openwellness_api/config.py
  - backend/api/src/openwellness_api/deps/auth_container.py
  - backend/api/src/openwellness_api/errors/handlers.py
  - backend/api/src/openwellness_api/main.py
  - backend/api/src/openwellness_api/resources/participant.py
  - backend/api/src/openwellness_api/schemas/_base.py
  - backend/api/src/openwellness_api/schemas/participant.py
  - backend/api/tests/conftest.py
  - backend/api/tests/test_auth_container.py
  - backend/api/tests/test_auth_service.py
  - backend/api/tests/test_participant_ids.py
  - backend/api/tests/test_refresh_session_repository.py
  - backend/api/tests/test_repository_errors.py
  - backend/api/tests/test_session_store.py
  - backend/api/tests/test_settings_env.py
  - backend/core/pyproject.toml
  - backend/core/src/openwellness_core/adapters/exceptions.py
  - backend/core/src/openwellness_core/adapters/mongo/repositories/__init__.py
  - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py
  - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_device_repository.py
  - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py
  - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_refresh_session_repository.py
  - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_user_repository.py
  - backend/core/src/openwellness_core/application/exceptions.py
  - backend/core/src/openwellness_core/application/repositories/__init__.py
  - backend/core/src/openwellness_core/application/repositories/refresh_session_repository.py
  - backend/core/src/openwellness_core/application/repositories/user_repository.py
  - backend/core/src/openwellness_core/domain/models/participant.py
  - backend/core/src/openwellness_core/infrastructure/config/settings.py
  - backend/core/src/openwellness_core/infrastructure/containers/repository_container.py
  - backend/core/tests/conftest.py
  - backend/core/tests/test_settings.py
  - backend/core/tests/test_smoke.py
  - backend/scheduler/src/openwellness_scheduler/config.py
  - backend/scheduler/tests/conftest.py
  - docker-compose.yml
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-30
**Depth:** standard
**Files Reviewed:** 41
**Status:** issues_found

## Summary

The phase moves refresh-session persistence behind a port, centralizes settings, strips `bson` out of the domain and API, and makes datastore errors honest. I traced the changed code against the pre-phase code (`git diff 5969fad HEAD`).

The refresh-rotation port refactor preserves the old behavior. This covers the CAS semantics, the reuse-then-revoke ordering, the rollback of the parent on a failed child insert, and the stored document shape. I found no regression in it. The settings consolidation also holds up: precedence is correct and the container image resolves `None` for the env file.

I found no blockers. The warnings are about HTTP semantics for bad input, a validation-error path that echoes stored data, and a lifespan cleanup gap. I did not run the full test suite. I did run `uv sync --frozen --extra dev --dry-run` at the workspace root, which resolves and installs the dev extras, so the CI install step is sound.

T-01-33 (409 on duplicate-email `POST /v1/users`) is accepted and not re-reported. I also did not re-report the pre-existing `_domain_exception` handler.

## Structural Findings (fallow)

None provided.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Malformed client-supplied reference ids return 404 NOT_FOUND instead of 400

**File:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py:56-62`
**Issue:** `_to_doc` raises `EntityNotFoundException(f"{alias} {value} not found")` when `assignedCoachId`, `userId` or `studyId` is not a valid ObjectId. For `POST /v1/studies/{study}/participants` and `PATCH .../{participant}`, `userId` and `assignedCoachId` come from the request body. A syntactically bad body field is a client error (400 INVALID_ARGUMENT), not "resource not found". The 404 also tells the client that a *different* resource is missing, and it echoes the raw client-supplied value into the response message. `test_malformed_reference_on_create_is_404` pins this behavior. This breaks the stable `/v1` AIP contract the project promises to keep. It is also a layering smell: a persistence adapter decides an HTTP-facing semantic.
**Fix:** Validate the id shape at the schema boundary instead, so FastAPI returns the standard 400. Keep the adapter guard as a defensive 404-or-ValueError path.
```python
# schemas/participant.py (create/update bodies)
ObjectIdStr = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{24}$")]
user_id: ObjectIdStr | None = None
assigned_coach_id: ObjectIdStr | None = None
```
Also map a bad `{study}` path segment on create to 404 deliberately, in the router rather than via the exception message. Drop the echoed `{value}` from the message.

### WR-02: Persistence-side ValidationError now reaches clients as a 400 that echoes stored document contents

**File:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py:71-77` with `backend/api/src/openwellness_api/errors/handlers.py:28-36,128-136`
**Issue:** `get_by_id` used to swallow every exception, including a `ValidationError` from `_from_doc`, and return `None`. It no longer does, which is the intended fix for honest outages. But a `pydantic.ValidationError` raised while hydrating a stored document (a server-side data problem) is now handled by `_pyd_validation`. That handler returns HTTP 400 `INVALID_ARGUMENT` with `details=exc.errors()`, and each error includes the `input` value. The result is a client-blamed 400, which is the wrong status, and the body leaks fields of the stored document (emails, ids). `_safe_errors` makes this *more* reachable by serializing arbitrary inputs. `get_by_query` and list endpoints already had this path. This phase extends it to single-document GETs and to `AuthService` lookups.
**Fix:** Strip `input` and `ctx` from the details, and do not treat a validation error that did not originate from the request as a 400.
```python
def _safe_errors(exc):
    return [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
```
Separately, let the persistence layer raise a domain/adapter exception, such as `AdapterException`, on hydrate failure so the catch-all returns a generic 500.

### WR-03: Lifespan "cleanup always runs" claim is false for the steps before the `try`

**File:** `backend/api/src/openwellness_api/main.py:50-58`
**Issue:** The comment says that after the Couchbase connection opens, all further setup runs inside the `try` so the `finally:` always cleans up. But `app.state.container = container` and `container.wire(modules=_WIRED_MODULES)` run *before* `try:`. If `wire` raises (for example a bad module in `RESOURCE_MODULES`), the already-open Couchbase cluster from `initialize()` is leaked and `unwire` is skipped. The misleading comment hides this from future readers. `refresh_repo.ensure_indexes()` is now also on the startup path and can raise `ServerSelectionTimeoutError` when Mongo is down. That one is correctly inside the `try`.
**Fix:** Move `try:` to immediately after `initialize()`.
```python
container.repositories.entity_repository().initialize()
try:
    app.state.container = container
    container.wire(modules=_WIRED_MODULES)
    ...
```

### WR-04: `ensure_indexes` reports every OperationFailure as an options-conflict

**File:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_refresh_session_repository.py:44-56`
**Issue:** The `except OperationFailure` re-raises `RuntimeError("... conflicting options — drop it manually and restart")` for any `OperationFailure`. Failures such as `Unauthorized` (the app user lacks `createIndex`), a duplicate `tokenHash` in legacy data blocking the unique build (E11000), or a quota error are all reported as an options conflict. This steers an operator to drop a live index, which is risky on the auth collection. The original cause is kept only in `__cause__`, so the startup log line is misleading.
**Fix:** Branch on the error code. Treat only `IndexOptionsConflict` (85) and `IndexKeySpecsConflict` (86) as a conflict, and let other failures propagate unchanged.
```python
except OperationFailure as exc:
    if exc.code in (85, 86):
        raise RuntimeError("... drop it manually and restart") from exc
    raise
```

## Info

### IN-01: Malformed or missing `OPENWELLNESS_ENV_FILE` is silently ignored

**File:** `backend/core/src/openwellness_core/infrastructure/config/settings.py:29-31`
**Issue:** `resolve_env_file` returns the override path without checking it exists. pydantic-settings skips a missing env file without error, so a typo in `OPENWELLNESS_ENV_FILE` silently falls back to code defaults (localhost datastores, `password`). The weak-secret boot guard catches the JWT and pepper only, not the datastore defaults.
**Fix:** If the override is set and `not Path(override).is_file()` (and it is not `os.devnull`), log a warning or raise at import. This is a one-line check.

### IN-02: `.env.example` documents none of the variables the boot guard requires

**File:** `.env.example:1-44`
**Issue:** The header says service-specific names (`API_AUTH_*`, `SMTP_*`) "live in the service config modules", but the template lists none of them. A self-hoster who copies it gets a startup `RuntimeError` for `API_AUTH_JWT_SECRET` and `API_AUTH_CODE_PEPPER` with no pointer. That cuts against the project's core value of working without tribal knowledge.
**Fix:** Add commented placeholders for `API_AUTH_JWT_SECRET` and `API_AUTH_CODE_PEPPER` (at least 32 chars; give a `openssl rand -hex 32` hint), plus `SMTP_*` and `API_CORS_ALLOWED_ORIGINS`.

### IN-03: Style and convention drift

**File:** `backend/api/src/openwellness_api/main.py:62`, `backend/api/tests/test_repository_errors.py:106-119,158-168`
**Issue:** The `refresh_session_collection.override(...)` line is about 110 columns, against the project's ~88 convention. `test_repository_errors.py` places imports mid-file (E402) in two places. `mongo_refresh_session_repository.py` and `refresh_session_repository.py` also carry docstring lines over 88 columns. The new adapter module lacks `from __future__ import annotations`, which the convention asks for in modules with non-trivial annotations.
**Fix:** Wrap the long lines and hoist the test imports to the top of the file.

### IN-04: Domain type annotation does not match what adapters hand back

**File:** `backend/core/src/openwellness_core/domain/models/participant.py:25-29`
**Issue:** `assigned_coach_id`/`user_id: Optional[str]` and `study_id: str = ""` are correct for new objects. But `MongoParticipant.study_id` defaults to `None`, and `to_domain` passes the field straight through. A legacy document without `studyId` hydrates a `Participant` with `study_id=None` despite the `str` annotation. Such a participant can be read but then fails every `save`/`PATCH` with the adapter's 404, and `_fetch` can never match it.
**Fix:** Coerce `None` to `""` in `MongoParticipant` (or `to_domain`) and add a test for a legacy document.

### IN-05: Catch-all 500 responses carry no CORS headers

**File:** `backend/api/src/openwellness_api/errors/handlers.py:157-176` (with `main.py:96-104`)
**Issue:** The `Exception` handler is installed in Starlette's `ServerErrorMiddleware`, which sits outside `CORSMiddleware`. The new honest-5xx path (datastore outage) therefore reaches the browser dashboard without `Access-Control-Allow-Origin`. The SPA sees an opaque network failure instead of the intended `INTERNAL` envelope. This is not a regression, since a bare 500 behaved the same before. It does undercut the point of the new outage tests, which use `TestClient`, not a browser.
**Fix:** Either accept this and document it, or add a small middleware inside `CORSMiddleware` that converts unhandled exceptions to the envelope.

---

_Reviewed: 2026-10-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
