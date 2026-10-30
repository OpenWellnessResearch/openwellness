---
phase: 01-foundations-architecture-decisions
reviewed: 2026-10-30T00:00:00Z
depth: standard
files_reviewed: 50
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
  - backend/README.md
  - backend/scheduler/src/openwellness_scheduler/config.py
  - backend/scheduler/tests/conftest.py
  - docker-compose.yml
  - docs/adr/0001-primary-key-format.md
  - docs/adr/0002-timestamp-representation.md
  - docs/adr/0003-soft-delete-archive-purge.md
  - docs/adr/0004-access-token-format.md
  - docs/adr/0005-owner-semantics.md
  - docs/adr/0006-coach-study-scope.md
  - docs/adr/0007-authorization-policy-table.md
  - docs/adr/README.md
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 1: Code Review Report (PR #6 scope)

**Reviewed:** 2026-10-30
**Depth:** standard
**Files Reviewed:** 50
**Status:** issues_found

## Summary

Scope is PR #6 (diff base e227a93f): CI workflows, shared settings, the refresh-session port and Mongo adapter, string participant ids, `DuplicateEntityException`, and ADRs 0001-0007.

Verified by running, not assumed:

- Core 83, api 227 and scheduler 4 tests pass against the PR tree (`uv sync --frozen --extra dev`, run in a temp venv).
- Dependency Rule holds. No `pymongo`, `bson`, `couchbase` or `celery` import exists under `backend/api/src`, `domain/` or `application/`. The only `bson` mention in `api/src` is a docstring in `errors/handlers.py`. Nothing imports `adapters` or `infrastructure` from `domain` or `application`.
- Anti-enumeration paths in `auth/service.py` are intact. The three-round-trip registration lookup is kept because the placeholder id `"0"*24` is a valid ObjectId. Registration still maps `DuplicateEntityException` to the uniform `invalid_code()`.
- Rotation and reuse-detection logic in the new `RefreshSessionStore` matches the old inline implementation step for step. The CAS filter, rollback-on-insert-failure and expiry ordering are unchanged.
- The CI action SHAs for checkout, setup-uv and gradle resolve on GitHub.
- ADR 0007 has 36 rows, equal to `len(RESOURCE_MODULES)`, with the same prefixes. ADR 0005 file:line citations match the code.

No blockers. The five warnings are: a legacy-data regression in the new participant adapter, a CORS gap in the new catch-all handler, two routes missing from the authorization ADR, the `.env` loading promise failing for the `APP_*` variables, and an unauthenticated email-existence oracle that is documented but active.

## Warnings

### WR-01: `MongoParticipantRepository._to_doc` makes legacy participants un-patchable and un-archivable, with a misleading 404

**File:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py:56-69`
**Issue:** `_to_doc` now raises `EntityNotFoundException` when any of `studyId`, `userId` or `assignedCoachId` is not a valid ObjectId. `_to_doc` runs on every `save()` (the `$set`) and on `archive()`, so it also runs on stored values the caller never touched.

I reproduced it against mongomock. A participant document with `userId: "legacy-couch-id"` reads fine. Then `repo.save(p)` fails with `EntityNotFoundException: userId legacy-couch-id not found`, and `repo.archive(id)` fails the same way.

Through the API this means `PATCH` and `DELETE /v1/studies/{s}/participants/{id}` return 404 for an existing participant. The 404 is also misleading, because the error is about a field value, not the participant. The message echoes the stored or supplied value back to the client.

The project constraint says legacy Couchbase/Mongo deployments must keep working, and this regresses them for any participant whose reference ids are not 24-hex strings.

Related type slip: for a document with no `studyId`, `get_by_id` returns `Participant.study_id = None`, although the field is now typed `str`.

**Fix:** Coerce only values that are valid ObjectIds and pass anything else through unchanged. Reject malformed input at the write boundary instead, as a 400/422 on the request schema:
```python
def _to_doc(self, entity):
    doc = super()._to_doc(entity)
    for alias in ("assignedCoachId", "userId", "studyId"):
        value = doc.get(alias)
        oid = object_id_or_none(value) if value else None
        doc[alias] = oid if oid is not None else (value or None)
    return doc
```
If strictness is wanted on create, validate `study` and `userId` with a pattern constraint on `ParticipantCreate` so the client gets a 400 rather than a 404. Do not put the offending value in the exception message. Add tests for `save`/`archive` over a legacy-string `userId` and for PATCH, which currently has no coverage in `test_participant_ids.py`.

### WR-02: New catch-all 500 handler returns no CORS headers, and every unhandled error is logged twice

**File:** `backend/api/src/openwellness_api/errors/handlers.py:169-189`
**Issue:** `@app.exception_handler(Exception)` is executed by Starlette's `ServerErrorMiddleware`, which sits outside `CORSMiddleware`. I confirmed it with a probe app. A request with `Origin: http://localhost:5173` to a route that raises `RuntimeError` gets `500` and no `access-control-allow-origin`. The same request to a `RedisError` route gets `503` and the header, and `/healthz` gets it too.

Since this PR turns datastore outages (previously swallowed) into 500s, the dashboard SPA will see an opaque network/CORS failure instead of the AIP-193 `INTERNAL` envelope. Its `DataError` mapping then cannot tell a 500 from being offline.

Starlette also re-raises the exception after the handler responds, so uvicorn logs the full traceback a second time. The handler's `logger.error(..., exc_info=exc)` is therefore a duplicate.

**Fix:** Either add CORS headers in the handler, or install the catch-all as middleware inside CORS. For the first option:
```python
origin = request.headers.get("origin")
headers = {"access-control-allow-origin": origin, "vary": "Origin"} \
    if origin in settings.cors_origins_list else {}
return JSONResponse(status_code=500, content=..., headers=headers)
```
Alternatively, add a small `BaseHTTPMiddleware` added before `CORSMiddleware`, so it runs inside it, that catches `Exception` and returns the envelope. This also avoids the double log.

### WR-03: ADR 0007 omits two live routes, and one of them can bypass the membership scope the ADR defines

**File:** `docs/adr/0007-authorization-policy-table.md:11,36,98-142` (routes in `backend/api/src/openwellness_api/resources/study.py:94`, `resources/conversation.py:106`)
**Issue:** The ADR states that each of the 36 modules "exposes the same seven operations", that a method "not listed in a cell is denied", that `/v1/auth:*` and `/healthz` are "the only anonymous surface", and that the Phase 2 policy tests are generated from the table rows.

Enumerating the live app shows 38 route bases. Two are in no row:

- `POST /v1/studies:lookup` looks a study up by name.
- `POST /v1/conversations:search` takes arbitrary `channels`/`kind`/`week` filters and returns matching conversations.

Generated tests will never cover them. A table-driven guard will either leave them open or reject them with no cell to consult. `conversations:search` is the dangerous one. A participant's access to conversations is supposed to be `self-member-conversation` (channel membership), and a coach's is `coach-study`. This endpoint filters by caller-chosen channels, so it is a scope-before-filter hazard of exactly the kind the ADR's own "scope before filter=" rule exists to prevent.

**Fix:** Add `lookup` (study) and `search` (conversation) to the table. Suggested cells:

- `studies:lookup`: admin, coach (`coach-study`), participant-self (`self-study`), with 404 outside scope.
- `conversations:search`: coach (`coach-study`), participant-self (`self-member-conversation`), with the scope predicate applied before the caller's filters.

Change the "seven operations" wording to "seven standard operations plus listed custom methods". Add a Phase 2 test that diffs `app.routes` against the table so a new route cannot be added without a policy cell.

### WR-04: `APP_*` variables listed in `.env.example` are read with `os.environ`, so they are silently ignored on direct runs

**File:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_app_repository.py:28-30` (with `.env.example:30-34`, `backend/core/src/openwellness_core/infrastructure/config/settings.py:10`, `backend/README.md:100-107`)
**Issue:** The PR's central promise is that one repo-root `.env` configures services whether started by compose or directly with `uvicorn` or `celery` from any directory. `OpenWellnessSettings` reads that file through pydantic-settings, which by design does not populate `os.environ`. `settings.py` even states it never mutates it.

`MongoAppRepository.create_app` still does `os.environ.get("APP_STORE_ID")`, and the same for `APP_IOS_BUNDLE_ID` and `APP_ONE_SIGNAL_APP_ID`. `.env.example` tells operators to set exactly these.

Under compose, `env_file` injects them, so it works. On a direct run from `.env` the values are None. App records are created with null store and bundle ids, with no error and no log.

**Fix:** Add an `AppSettings(OpenWellnessSettings)` with `env_prefix="APP_"` and fields `store_id`, `ios_bundle_id`, `one_signal_app_id`, and expose it on `AppConfig`. Inject it into `MongoAppRepository`. If that is out of scope for this PR, document in `.env.example` and the README that `APP_*` is compose-only until migrated.

### WR-05: Unauthenticated `POST /v1/users` now answers 409 ALREADY_EXISTS, an email-existence oracle

**File:** `backend/api/src/openwellness_api/errors/handlers.py:87-102` (accepted gap recorded in `docs/adr/0007-authorization-policy-table.md:140`)
**Issue:** `AuthSettings.enforce_principal` defaults to False, and the ADR says every `/v1` route is anonymous until Phase 2. Any caller can therefore POST `{"email": "<candidate>"}` to `/v1/users` and learn from 201 versus 409 whether an account exists. For a platform holding participant health data this is the enumeration the project's auth rules forbid, and the new handler makes it a clean, stable signal. Before this PR the duplicate was an unhandled error. The ADR and the handler docstring record the gap as accepted, but they do not mitigate it, and nothing in the repo blocks deploying in the interim.

**Fix:** Pick one:

- Keep the 409 but gate the user-create route behind the Phase 2 admin dependency before any build that can be deployed. Add a failing/xfail test that asserts `POST /v1/users` without a principal is 401, so the gap cannot be forgotten.
- Return the same 201-shaped or 400 uniform response for duplicates on this route until auth is enforced.
- At minimum, add a startup warning when `enforce_principal` is False and note the gap prominently in `backend/README.md`.

## Info

### IN-01: `.env.example` omits settings the API refuses to boot without

**File:** `.env.example:1-44`
**Issue:** The rewritten header says it lists the names. The API's lifespan refuses to start unless `API_AUTH_JWT_SECRET` and `API_AUTH_CODE_PEPPER` are each at least 32 characters (`main.py:36-46`). Neither is in the file, nor are `SMTP_*` or `API_CORS_ALLOWED_ORIGINS`. Someone following the file's own instructions hits a `RuntimeError` at boot with no pointer to the cause.
**Fix:** Add commented entries with a generation hint, e.g. `# API_AUTH_JWT_SECRET=  (>=32 chars: python -c "import secrets;print(secrets.token_urlsafe(48))")`, and likewise for the pepper and SMTP.

### IN-02: CI concurrency group cancels in-progress runs on `main`

**File:** `.github/workflows/ci.yml:10-12`
**Issue:** `cancel-in-progress: true` with the group `ci-${{ pull_request.number || github.ref }}` also applies to `push` on `main`. Two quick merges cancel the first merge commit's run, so a commit on `main` can end with no result.
**Fix:** `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.

### IN-03: Dependency Rule is asserted in docs but not enforced by any test or CI step

**File:** `.github/workflows/ci.yml:23-58` (and `backend/core/tests`)
**Issue:** I verified by grep that the rule holds today. Nothing prevents regression: there is no import-linter step and no AST test that fails on `bson`, `pymongo`, `couchbase` or `redis` under `domain/`, `application/` or `api/src`. `FOUND-04` was a reintroduction-prone leak, since `bson` was in `domain/models/participant.py` and `schemas/_base.py` until this PR.
**Fix:** Add a small pytest that walks `ast` over those trees and asserts the forbidden import set is empty, and run it in the existing core test step.

### IN-04: Unused parameter and a duplicated default collection name

**File:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py:51`; `backend/core/src/openwellness_core/infrastructure/containers/repository_container.py:~334`
**Issue:** `_duplicate(self, exc)` never uses `exc`. The string `"auth_refresh_sessions"` is now defined twice (in `AuthSettings.refresh_collection` and the container's `DIObject`), guarded only by a test. The `refresh_session` Singleton also caches the collection at first resolution, so a later `refresh_session_collection.override(...)` is silently ignored.
**Fix:** Drop `exc` from `_duplicate`. Keep the single default and let the lifespan always override it. Note in the container comment that the override must precede the first `refresh_session()` call.

### IN-05: Style drift from project conventions in new files

**File:** `backend/api/src/openwellness_api/main.py:67,70`; `backend/api/tests/test_repository_errors.py:76-86,167-171`
**Issue:** Two `main.py` lines exceed the ~88-column convention. `test_repository_errors.py` places imports mid-file after test functions, which would be E402 under any linter. `test_participant_ids.py` covers create, get and list, but not PATCH or DELETE, which are the paths whose `_coerce_object_ids` handling was removed.
**Fix:** Wrap the lines, move the imports to the top, and add PATCH/DELETE participant tests (see WR-01).

### IN-06: `resolve_env_file` locates the repo root by the `docker-compose.yml` marker and `env_file` is bound at import

**File:** `backend/core/src/openwellness_core/infrastructure/config/settings.py:40-47,50-55`
**Issue:** The `# shortcut:` comment documents the marker. Two limits are not noted. First, `OPENWELLNESS_ENV_FILE` is read once at class-definition time, so setting it after import has no effect on the module-level classes. `test_settings_env.py` works around this with subprocesses, but operators embedding the package would not know. Second, the first ancestor containing `docker-compose.yml` wins, so an install under an unrelated checkout that has its own compose file would pick up that directory's `.env`.
**Fix:** Add one line to the module docstring stating that the override must be set before the first import. Optionally also require `backend/pyproject.toml` beside the compose file.

---

_Reviewed: 2026-10-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
