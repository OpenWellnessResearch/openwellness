# Codebase Concerns

**Analysis Date:** 2026-10-29

## Tech Debt

**Resource routes never authenticate (see Security Considerations for the risk):**
- Issue: Of 260 HTTP route decorators under `backend/api/src/openwellness_api/resources/`, none depend on `require_principal`, `verify_access`, or `auth_service_dep`. The 36 resource modules that import `get_principal` only use it to stamp `updated_by`. `get_principal` never rejects a request, so authentication is effectively optional on every resource.
- Files: `backend/api/src/openwellness_api/deps/principal.py`, `backend/api/src/openwellness_api/resources/*.py`, `backend/api/src/openwellness_api/v1.py`
- Impact: Protected-looking data routes are reachable without credentials. The enforcement gate (`require_principal`) is dead code because nothing calls it.
- Fix approach: Apply a strict dependency at the `v1` router level (or per-resource) for everything except `/v1/auth:*` and `/healthz`. Owner-scoped routes should also check that the JWT `sub` (or `participant` claim) matches the `{user}` path segment. Only then flip `API_AUTH_ENFORCE_PRINCIPAL` on.

**Permissive principal rollout is the default:**
- Issue: `AuthSettings.enforce_principal` defaults to `False` (`backend/api/src/openwellness_api/config.py`). `require_principal` only logs a would-be 401 and lets the anonymous principal through.
- Files: `backend/api/src/openwellness_api/config.py`, `backend/api/src/openwellness_api/deps/principal.py`
- Impact: Even routes that opt into `require_principal` will not reject unauthenticated callers unless the env var is set in each environment.
- Fix approach: Default to `True` in production, or make the setting required in `.env` (see `.env.example`, which does not list `API_AUTH_*` variables at all).

**Legacy `verified_id` derivation is a stub:**
- Issue: `AuthService._verified_marker` in `backend/api/src/openwellness_api/auth/service.py` documents a legacy bcrypt variant that is "intentionally NOT implemented". `AuthSettings.legacy_verified_id_salt` in `backend/api/src/openwellness_api/config.py` is never read.
- Files: `backend/api/src/openwellness_api/auth/service.py`, `backend/api/src/openwellness_api/config.py`
- Impact: Dead configuration that suggests a migration path that does not exist. If a legacy-migrated deployment sets the salt expecting compatibility, login/registration checks will silently disagree with existing `verified_id` values.
- Fix approach: Remove the field, or implement the legacy path and add a test that proves compatibility with pre-existing markers.

**Duplicated settings classes between API and scheduler:**
- Issue: `CouchbaseSettings`, `SyncGatewaySettings`, `MongoSettings`, and `AppConfig` are defined separately in `backend/api/src/openwellness_api/config.py` and `backend/scheduler/src/openwellness_scheduler/config.py`, with identical defaults.
- Impact: A default or env-prefix change must be made in two places, and they can drift.
- Fix approach: Move the shared settings into `backend/core/src/openwellness_core/infrastructure/config/` and import them from both services.

**Broad exception swallowing in repositories:**
- Issue: `MongoBaseRepository.get_by_id` in `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py` catches every exception and returns `None`, after `print`-ing the full traceback. Connection failures and malformed ids therefore look like "not found" (a 404). `unarchive` also catches and silently returns.
- Impact: Real database outages are masked as missing data, and errors are logged with `print` instead of `logging`.
- Fix approach: Catch only `bson.errors.InvalidId` (return `None`) and let other errors propagate to the global handlers in `backend/api/src/openwellness_api/errors/handlers.py`. Replace `print` with `logger`.

**Dynamic query construction in the Mongo base repository:**
- Issue: `MongoBaseRepository.execute_query(query: dict)` passes a caller-supplied dict straight to `collection.find`. Any caller that forwards request-derived dicts can inject Mongo operators (for example `$where` or `$ne`).
- Files: `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py`
- Fix approach: Restrict callers to typed query builders, or validate keys against an allowlist before the call.

**Scheduler ships with no scheduled jobs:**
- Issue: The only scheduler task is `count_study_participants` in `backend/scheduler/src/openwellness_scheduler/infrastructure/tasks.py`. Its beat schedule exists only as a commented-out example in `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`, so no periodic work runs by default.
- Impact: The scheduler container (`docker-compose.yml`) starts a worker with no scheduled jobs and no beat process.
- Fix approach: Add a `beat` service to `docker-compose.yml`, or document that the worker is intentionally on-demand only.

## Known Bugs

**Dashboard feature coverage is limited to auth:**
- Symptoms: Only `frontend/dashboard/src/features/auth/` has test files. Other dashboard features have no tests.
- Files: `frontend/dashboard/src/features/`
- Trigger: Any regression in non-auth dashboard screens will not be caught by `npm run test`.
- Workaround: Manual QA.

**Scheduler task is not reachable on a timer:**
- Symptoms: `count_study_participants` only runs when enqueued manually. Operators who expect hourly counts from the deployed stack will see stale or missing data.
- Files: `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`
- Trigger: Deploy via `docker-compose.yml` without enabling the commented-out `beat_schedule`.
- Workaround: Enqueue the task manually or enable the beat schedule.

## Security Considerations

**Unauthenticated access to user and owner-scoped data:**
- Risk: Any unauthenticated HTTP client can call `GET /v1/users`, `GET /v1/users/{user}`, `PATCH`/`DELETE /v1/users/{user}`, and the owner-scoped sub-resources (for example `/v1/users/{user}/weights`). `DELETE` and `:purge` are also reachable without credentials. Anyone who learns or enumerates a user id can read or alter that user's health data.
- Files: `backend/api/src/openwellness_api/resources/user.py`, `backend/api/src/openwellness_api/resources/weight.py` (representative of all owner-scoped resources), `backend/api/src/openwellness_api/resources/admin.py`
- Current mitigation: Owner-scoped routes return 404 when the entity does not belong to the `{user}` path segment (`check_parent` in `backend/api/src/openwellness_api/common/handlers.py`). This prevents cross-owner confusion but not unauthenticated access. Admin routes are not gated by any admin role check.
- Recommendations: Require a verified bearer token on all `/v1` routes except `/v1/auth:*`. Bind the token's `sub` or `participant` claim to `{user}` for owner routes. Require an admin role for `resources/admin.py` and `GET /v1/users` (list). Add an integration test that asserts 401 for an anonymous call to each resource.

**`X-Principal-Id` header is trusted for audit stamping:**
- Risk: `get_principal` falls back to the caller-supplied `X-Principal-Id` header when there is no valid bearer token (`backend/api/src/openwellness_api/deps/principal.py`). Audit fields such as `updated_by` can therefore be forged.
- Files: `backend/api/src/openwellness_api/deps/principal.py`, `backend/api/src/openwellness_api/common/handlers.py` (`stamp_audit`)
- Current mitigation: None for anonymous requests.
- Recommendations: Ignore `X-Principal-Id` unless the request is authenticated, or remove it entirely once bearer auth is enforced.

**Rate limiting trusts `X-Forwarded-For`:**
- Risk: `_client_ip` in `backend/api/src/openwellness_api/auth/router.py` uses the first `X-Forwarded-For` hop as the client IP. The per-IP send limit (`API_AUTH_IP_MAX_PER_WINDOW`) can be bypassed by sending a fresh header on every request, and an attacker can also use it to exhaust a victim's IP quota.
- Files: `backend/api/src/openwellness_api/auth/router.py`
- Current mitigation: Per-email send limits and resend cooldown (`backend/api/src/openwellness_api/auth/otp_store.py`) still apply.
- Recommendations: Honor `X-Forwarded-For` only from trusted proxy addresses (for example via uvicorn `--proxy-headers` with `--forwarded-allow-ips`), and document the deployment's proxy chain.

**Insecure default credentials in settings classes:**
- Risk: `CouchbaseSettings.password` defaults to `"password"` and `username` to `"Administrator"` in both `backend/api/src/openwellness_api/config.py` and `backend/scheduler/src/openwellness_scheduler/config.py`. `MongoSettings.url` defaults to an unauthenticated local URL.
- Files: `backend/api/src/openwellness_api/config.py`, `backend/scheduler/src/openwellness_scheduler/config.py`
- Current mitigation: `.env.example` leaves credentials empty, and the API boot guard enforces JWT secret and pepper length (`backend/api/src/openwellness_api/main.py`). Nothing enforces the Couchbase or Mongo credentials at boot.
- Recommendations: Remove the default password and fail fast when `COUCHBASE_PASSWORD` is unset. Apply the same guard to the scheduler.

**Refresh token stored in `localStorage`:**
- Risk: The dashboard keeps the refresh token in `localStorage` under `openwellness.refreshToken` (`frontend/dashboard/src/core/auth/tokenStorage.ts`). Any XSS in the dashboard can read it and mint sessions until revoked.
- Files: `frontend/dashboard/src/core/auth/tokenStorage.ts`
- Current mitigation: The access token is kept in module memory only, and refresh tokens are rotated and reuse-detected server-side (`backend/api/src/openwellness_api/auth/session_store.py`).
- Recommendations: Move the refresh token to an `HttpOnly`, `Secure`, `SameSite` cookie scoped to the auth path, and add a Content-Security-Policy to `frontend/dashboard/index.html`.

**Tracebacks written to stdout:**
- Risk: `MongoBaseRepository.get_by_id` prints full tracebacks and error text, which can contain document ids or query contents. These go into container logs with no redaction.
- Files: `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py`
- Current mitigation: None.
- Recommendations: Switch to `logging` with a structured logger and redact identifiers.

## Performance Bottlenecks

**Unbounded Mongo reads via `list_all`:**
- Problem: `MongoBaseRepository.list_all` calls `get_by_query({})`, which materializes every document in the collection into memory.
- Files: `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py`
- Cause: No limit or cursor streaming.
- Improvement path: Remove `list_all` from callers that operate on user-scale collections, or make it a paginated generator.

**Synchronous I/O in request handlers:**
- Problem: `backend/api/src/openwellness_api/auth/router.py` deliberately uses sync `def` handlers so FastAPI runs them in a threadpool. Redis, SMTP, and Couchbase calls all block a worker thread. `uvicorn` is started with `--workers 2` in `backend/Dockerfile`.
- Files: `backend/api/src/openwellness_api/auth/router.py`, `backend/Dockerfile`
- Cause: Blocking drivers (`redis`, `smtplib`, `pymongo`, Couchbase SDK).
- Improvement path: Size the threadpool explicitly, or move to async drivers. Measure before changing: two workers may be the bottleneck or may be ample.

**Per-request email send:**
- Problem: Email delivery uses `BackgroundTasks` when a scheduler is supplied, but without a durable queue. A process restart drops in-flight OTP emails.
- Files: `backend/api/src/openwellness_api/auth/service.py` (`_send_email`), `backend/api/src/openwellness_api/auth/email_sender.py`
- Cause: Background task runs in the API worker process.
- Improvement path: Enqueue OTP sends through the Celery broker (`backend/scheduler`) so they survive restarts.

## Fragile Areas

**N1QL query construction:**
- Files: `backend/core/src/openwellness_core/adapters/couchbase/repositories/*.py`, `backend/core/scripts/check_no_fstring_n1ql.py`
- Why fragile: Queries are built as f-strings with a bucket reference and `' AND '.join(clauses)`. The lint script (`backend/core/scripts/check_no_fstring_n1ql.py`) currently passes (exit 0), but it only forbids interpolation other than an allowlist, and it is documented as a manual or pre-commit check. Nothing in CI runs it.
- Safe modification: Add any new filter as a named parameter (`$name`), never as an interpolated value. Run `python backend/core/scripts/check_no_fstring_n1ql.py` before committing.
- Test coverage: `backend/core/tests/test_repositories_queries.py` exists, but there is no CI workflow in the repository that runs it.

**Redis client decoding requirement:**
- Files: `backend/api/src/openwellness_api/auth/otp_store.py`
- Why fragile: `RedisOtpStore` requires a Redis client built with `decode_responses=True`. It raises at construction if this is wrong, which is good, but the requirement is only enforced at runtime and in the container factory (`backend/api/src/openwellness_api/deps/auth_container.py`).
- Safe modification: Keep `decode_responses=True` wherever the client is constructed. Tests use `fakeredis.FakeRedis`, which must match.
- Test coverage: `backend/api/tests/test_otp_store.py` covers the store, not the production container wiring.

**Refresh-session index options are immutable in place:**
- Files: `backend/api/src/openwellness_api/auth/session_store.py` (`ensure_indexes`)
- Why fragile: The indexes are created with fixed names. Changing `unique` or `expireAfterSeconds` later raises `IndexOptionsConflict` on real Mongo, and the code comment says a manual `dropIndex` is required before restart.
- Safe modification: Never change index options in code without a migration step. Add a migration note to the PR.
- Test coverage: Tests run against `mongomock`, which does not enforce index option conflicts or the TTL sweep.

**Startup ordering in the API lifespan:**
- Files: `backend/api/src/openwellness_api/main.py`
- Why fragile: The lifespan opens Couchbase before the try block that guarantees cleanup, and the Redis ping is best-effort. A failure between `container.wire` and `try:` leaves Couchbase open.
- Safe modification: Move `container.wire` and the Couchbase initialize call inside the `try`, or register a cleanup callback before opening it.
- Test coverage: The test app fixture does not run the lifespan, so this path is not exercised by tests.

## Scaling Limits

**Two uvicorn workers with per-process clients:**
- Current capacity: `--workers 2` in `backend/Dockerfile`, one Couchbase cluster and one Redis client per worker.
- Limit: Connection count grows with worker count, and the synchronous request model caps throughput per worker.
- Scaling path: Increase workers only after moving blocking calls off the event loop (see Performance Bottlenecks).

**Redis single-instance dependency:**
- Current capacity: One `redis:7-alpine` service in `docker-compose.yml` with no persistence configuration and no replica.
- Limit: OTP records, rate-limit counters, and the Celery broker all depend on that one instance. A restart clears OTP codes and rate-limit windows, and it drops queued Celery tasks.
- Scaling path: Enable AOF persistence in `docker-compose.yml`, or use a managed Redis for production.

**Mongo refresh-session TTL is best-effort:**
- Current capacity: Expired refresh sessions are removed by the Mongo TTL monitor, which runs about once a minute.
- Limit: Stale rows persist until the monitor runs. Correctness depends on the explicit expiry check in `RefreshSessionStore`, so this is a storage-growth concern, not a security one.
- Scaling path: Add periodic cleanup, or monitor collection size.

## Dependencies at Risk

**Frontend build toolchain is on very new major versions:**
- Risk: `frontend/dashboard/package.json` pins `typescript ~6.0.2`, `vite ^8.0.12`, `eslint ^10.3.0`, `react ^19.2.6`, and `jsdom ^29.1.1`. These are very recent majors, and plugins such as `eslint-plugin-react-hooks ^7.1.1` and `typescript-eslint ^8.59.2` may lag them.
- Impact: Lint or typecheck breakage on fresh installs. The lockfile (`frontend/dashboard/package-lock.json`) mitigates this for reproducible installs.
- Migration plan: Keep the lockfile committed, and run `npm run typecheck && npm run lint` in CI on every upgrade.

**Backend `pyjwt` and `redis` coupling:**
- Risk: `backend/api/src/openwellness_api/auth/token_service.py` depends on PyJWT behavior for the `options={"require": [...]}` form and for the `leeway` argument. Upgrading PyJWT major versions can change these defaults.
- Impact: Silent acceptance or rejection of tokens after an upgrade.
- Migration plan: Pin the version in `backend/api/pyproject.toml` and cover `verify_access` with tests for each required claim (`backend/api/tests/test_token_service.py` already exercises this).

## Missing Critical Features

**No authorization model:**
- Problem: There are no roles enforced anywhere. `AccessClaims.roles` is parsed from the token, but no route checks it. `AdminRepository` exists without an admin gate.
- Blocks: Safe exposure of admin endpoints and of multi-tenant data to real users.

**No CI pipeline in the repository:**
- Problem: No `.github/` directory, `.pre-commit-config.yaml`, or `Makefile` is present. The N1QL lint, the backend test suite, and the frontend typecheck/lint/test commands are only run by hand.
- Blocks: Any gate on the regressions described above.

**No audit log for admin or owner data changes:**
- Problem: `stamp_audit` records `updated_by` from the spoofable principal header, and nothing is written to a separate audit store.
- Blocks: Forensics after a data-modification incident.

## Test Coverage Gaps

**Auth routes are not tested against unauthenticated access to resources:**
- What's not tested: No test asserts that a resource route rejects a request without a token. The test set in `backend/api/tests/` covers token mechanics and owner-scoped CRUD (`test_users_crud.py`, `test_weights_owner_crud.py`) with the principal in permissive mode.
- Files: `backend/api/tests/test_users_crud.py`, `backend/api/tests/test_weights_owner_crud.py`, `backend/api/tests/test_principal.py`
- Risk: The unauthenticated-access gap described above can ship unnoticed.
- Priority: High

**No end-to-end test of the Couchbase or Mongo adapters:**
- What's not tested: Real database behavior, including index conflicts, TTL expiry, and N1QL parameter binding. Tests use `mongomock` and fakes.
- Files: `backend/core/tests/test_repositories_queries.py`, `backend/api/tests/test_session_store.py`
- Risk: Production-only failures in the refresh-session index and query paths.
- Priority: Medium

**Scheduler container not covered by deployment checks:**
- What's not tested: The `scheduler` service in `docker-compose.yml` has no health check, and `backend/scheduler/tests/test_tasks.py` exercises tasks through a replaced container rather than a running worker.
- Files: `backend/scheduler/tests/test_tasks.py`, `docker-compose.yml`
- Risk: The worker can fail to connect to Couchbase or the broker without a test noticing.
- Priority: Low

**Frontend feature modules untested:**
- What's not tested: Only `core/api`, `core/auth`, and the app shell have tests in `frontend/dashboard/src`. Feature modules are not covered.
- Files: `frontend/dashboard/src/features/`
- Risk: Regressions in dashboard screens.
- Priority: Medium

---

*Concerns audit: 2026-10-29*
