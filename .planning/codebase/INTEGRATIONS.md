# External Integrations

**Analysis Date:** 2026-10-29

## APIs & External Services

**Outbound third-party HTTP APIs:**
- None detected. No SDK or direct HTTP client calls to Fitbit, OneSignal, Stripe, or similar services were found in `backend/`. Fitbit appears only as a data model: records are stored in the database by the `fitbit*` resources and repositories (`backend/api/src/openwellness_api/resources/fitbit*.py`, `backend/core/src/openwellness_core/adapters/couchbase/repositories/cb_fitbit_*.py`). Fitbit data is therefore ingested by an external process, not by this codebase.
- OneSignal is referenced only as a stored identifier. `APP_ONE_SIGNAL_APP_ID` (`.env.example`) is a default value stamped onto App entities by `AppRepository.create_app` (`backend/core/src/openwellness_core/application/repositories/app_repository.py`). No OneSignal SDK is called.

**Outbound email (SMTP):**
- Purpose: sending one-time passcodes for login and registration.
  - Implementation: `backend/api/src/openwellness_api/auth/email_sender.py`, class `SmtpEmailSender`.
  - Protocol: stdlib `smtplib.SMTP(host, port)` with `starttls()` when `use_tls` is set. Default port 587.
  - Auth: `SMTP_USERNAME` and `SMTP_PASSWORD` (`backend/api/src/openwellness_api/config.py`, class `SmtpSettings`).
  - Other env: `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM_ADDRESS`, `SMTP_USE_TLS`.
  - Test double: `FakeEmailSender` in the same module; never sends real mail.

**Mobile to backend:**
- Ktor HTTP client in `frontend/mobile/core/data/src/commonMain/kotlin/edu/openwellness/mobile/core/data/di/CoreDataModule.kt` with `defaultRequest { url(config.baseUrl) }`.
- Base URL comes from `BuildConfig.API_BASE_URL` on Android (`frontend/mobile/androidApp/build.gradle.kts`) and from a hardcoded value on iOS (`frontend/mobile/iosApp/iosApp/iOSApp.swift`).

**Dashboard to backend:**
- `fetch`-based client in `frontend/dashboard/src/core/api/apiClient.ts`. Base URL from `VITE_API_BASE_URL` (`frontend/dashboard/src/core/api/env.ts`).

## Data Storage

**Couchbase (primary document store):**
- Connection: `COUCHBASE_URL`, `COUCHBASE_USERNAME`, `COUCHBASE_PASSWORD`, `COUCHBASE_BUCKET_NAME` (`backend/api/src/openwellness_api/config.py`, `backend/scheduler/src/openwellness_scheduler/config.py`).
- Client: Couchbase Python SDK 4.x (`couchbase.cluster.Cluster`, `couchbase.auth.PasswordAuthenticator`) in `backend/core/src/openwellness_core/infrastructure/drivers/cb_entity_repository.py`. Opened once per process by `initialize()`, closed by `cleanup()`.
- Queries: N1QL through the SDK. Identifiers are allowlisted and values are named parameters. Enforced by `backend/core/src/openwellness_core/adapters/couchbase/repositories/_query_helpers.py` and the linter `backend/core/scripts/check_no_fstring_n1ql.py`.
- Repositories: `backend/core/src/openwellness_core/adapters/couchbase/repositories/cb_*.py`. These cover entities such as sessions, conversations, posts, goals, survey results, Fitbit sleep/weight/heart records, actigraph records, cards, and study settings. Wiring: `backend/core/src/openwellness_core/infrastructure/containers/repository_container.py`.

**Couchbase Sync Gateway (HTTP):**
- Purpose: document CRUD over HTTP on top of the Couchbase bucket.
- Connection: `SYNC_GATEWAY_URL` (`backend/core/src/openwellness_core/infrastructure/config/app_config.py` defines the protocol; the concrete value is read in `backend/api/src/openwellness_api/config.py` and `backend/scheduler/src/openwellness_scheduler/config.py`). Default `http://localhost:4984/openwellness`.
- Client: `requests` with 10-second timeouts. Calls `get`, `post`, `put`, and `delete` in `backend/core/src/openwellness_core/infrastructure/drivers/cb_entity_repository.py`.

**MongoDB (secondary document store):**
- Connection: `MONGO_URL` and `MONGO_DB` (`backend/api/src/openwellness_api/config.py`, `backend/core/src/openwellness_core/infrastructure/drivers/mdb_collection_repository.py`).
- Client: `pymongo.MongoClient`, constructed once per `MDBCollectionRepository`. Version pinned to `>=4.7,<4.14` for MongoDB 4.0 compatibility.
- Entities stored in Mongo (repos in `backend/core/src/openwellness_core/adapters/mongo/repositories/`): `user`, `admin`, `app`, `device`, `fitbit`, `participant`, `study`, and `study_message`.
- Models: `backend/core/src/openwellness_core/adapters/mongo/model/`.
- Auth refresh sessions: collection named by `API_AUTH_REFRESH_COLLECTION` (default `auth_refresh_sessions`), managed by `backend/api/src/openwellness_api/auth/session_store.py`. Indexes created by `ensure_indexes()` at startup, including a TTL index.
- Deployment note: the Mongo instance is published by an `opserver` on the VM host and reached through `host.docker.internal` (`docker-compose.yml`, `.env.example`). The app user authenticates against the app DB (`authSource=<db>`).

**Redis:**
- Purpose: OTP storage, verification attempts, and rate-limit counters (`backend/api/src/openwellness_api/auth/otp_store.py`).
- Client: `redis.Redis.from_url` with `decode_responses=True`, `socket_connect_timeout=3`, `socket_timeout=5`. Built in `backend/api/src/openwellness_api/deps/auth_container.py`.
- Connection: `REDIS_URL` (`backend/api/src/openwellness_api/config.py`, default `redis://localhost:6379/0`).
- Also used as the Celery broker and result backend (see Task Queue).
- Container: `redis:7-alpine` service in `docker-compose.yml`.

**File Storage:**
- Not detected as a cloud service. Asset metadata is stored through `backend/core/src/openwellness_core/adapters/couchbase/repositories/cb_asset_repository.py`. No S3, GCS, or Azure blob SDK found.

**Caching:**
- Redis (see above) for OTP and rate limits. No separate application cache layer detected.

## Task Queue

**Celery:**
- Broker: `CELERY_BROKER_URL` (default `redis://localhost:6379/0`, compose value `redis://redis:6379/0`).
- Result backend: `CELERY_RESULT_BACKEND` (default `redis://localhost:6379/1`, compose value `redis://redis:6379/1`).
- Config: `backend/scheduler/src/openwellness_scheduler/config.py` (`CelerySettings`), `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`.
- Queue: `openwellness` (`task_default_queue`).
- Tasks: `openwellness.count_study_participants` in `backend/scheduler/src/openwellness_scheduler/infrastructure/tasks.py`.
- Beat: no schedule is active. The example `beat_schedule` in `celery_app.py` is commented out.
- Worker lifecycle: opens Couchbase on `worker_process_init` and closes it on `worker_process_shutdown` (`celery_app.py`).

## Authentication & Identity

**Custom email OTP with JWT sessions:**
- No external identity provider. Authentication is implemented in-house.
  - OTP generation and verification: `backend/api/src/openwellness_api/auth/service.py`, `backend/api/src/openwellness_api/auth/otp_store.py`. OTP is peppered with `API_AUTH_CODE_PEPPER`.
  - Access tokens: HS256 JWTs signed with `API_AUTH_JWT_SECRET`, issuer and audience `openwellness-api`. Implemented in `backend/api/src/openwellness_api/auth/token_service.py` using `pyjwt`. Lifetime 900 seconds.
  - Refresh tokens: opaque CSPRNG values, stored only as SHA-256 hashes in Mongo (`backend/api/src/openwellness_api/auth/session_store.py`). Lifetime 2,592,000 seconds (30 days).
  - Principal resolution: `backend/api/src/openwellness_api/deps/principal.py`. Enforcement toggled by `API_AUTH_ENFORCE_PRINCIPAL`.
- Routes: `backend/api/src/openwellness_api/auth/router.py`, mounted in `backend/api/src/openwellness_api/v1.py`.
- Client token storage:
  - Dashboard: access token kept in memory, refresh token in `localStorage` under a documented key (`frontend/dashboard/src/core/auth/tokenStorage.ts`).
  - Mobile: DataStore Preferences via `frontend/mobile/core/data/src/commonMain/kotlin/edu/openwellness/mobile/core/data/auth/DataStoreAuthTokenStorage.kt`, with iOS storage rooted in the Documents directory (`DataStoreFactory.ios.kt`). Ktor `Auth` bearer plugin performs refresh.

## Monitoring & Observability

**Error Tracking:**
- None detected. No Sentry, Crashlytics, Datadog, or similar SDK in the repo.

**Logs:**
- Python `logging` module with module-level loggers (for example `backend/api/src/openwellness_api/main.py`, `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`). Written to stdout/stderr and captured by Docker.
- OTP codes and raw email addresses are excluded from logs by design (`backend/api/src/openwellness_api/auth/email_sender.py`). Email is logged as a SHA-256 digest.

**Health:**
- `GET /healthz` returns `{"status": "ok"}` (`backend/api/src/openwellness_api/main.py`). Used by the Docker `HEALTHCHECK` in `backend/Dockerfile`.

## CI/CD & Deployment

**Hosting:**
- Single VM running Docker Compose (`docker-compose.yml`). Images built from `backend/Dockerfile`.
- API exposed on `127.0.0.1:8200` (host) to container port 8000. Described in the compose file as tunnel-only.

**CI Pipeline:**
- Not detected. No `.github/workflows`, `.gitlab-ci.yml`, or similar configuration was found in the repo.
- Pre-commit hook referenced in `backend/core/scripts/check_no_fstring_n1ql.py` is maintained outside the repo.

## Environment Configuration

**Required env vars (from `.env.example` and settings classes):**
- Couchbase: `COUCHBASE_URL`, `COUCHBASE_USERNAME`, `COUCHBASE_PASSWORD`, `COUCHBASE_BUCKET_NAME`
- Mongo: `MONGO_URL`, `MONGO_DB`
- Sync Gateway: `SYNC_GATEWAY_URL`
- API: `API_TITLE`, `API_CORS_ALLOWED_ORIGINS`
- Auth: `API_AUTH_JWT_SECRET` (32+ chars), `API_AUTH_CODE_PEPPER` (32+ chars), `API_AUTH_REFRESH_COLLECTION`
- Redis: `REDIS_URL`
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_ADDRESS`
- Celery: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- App defaults: `APP_STORE_ID`, `APP_IOS_BUNDLE_ID`, `APP_ONE_SIGNAL_APP_ID`
- Dashboard (build time): `VITE_API_BASE_URL`

**Secrets location:**
- Runtime secrets are supplied through `.env` at the repo root on the VM (`docker-compose.yml` uses `env_file: .env`). `.env` is git-ignored (`.gitignore`), and `.env.example` documents the variable names.
- Dashboard `.env` files are also git-ignored (`frontend/dashboard/.gitignore`).
- Mobile signing or local secrets are kept out of the repo through `frontend/mobile/.gitignore` (`local.properties`).
- Note: `backend/api/src/openwellness_api/config.py` and `backend/scheduler/src/openwellness_scheduler/config.py` contain fallback defaults for Couchbase credentials (`Administrator` / `password`). These apply only if the env vars are unset.

## Webhooks & Callbacks

**Incoming:**
- None detected. No webhook route receives external callbacks. The v1 router mounts only resource CRUD and auth endpoints (`backend/api/src/openwellness_api/v1.py`, `backend/api/src/openwellness_api/resources/`).

**Outgoing:**
- None detected. The only outbound network calls from the backend are Couchbase SDK connections, Sync Gateway HTTP, MongoDB, Redis, and SMTP.

---

*Integration audit: 2026-10-29*
