# Technology Stack

**Analysis Date:** 2026-10-29

## Languages

**Primary:**
- Python 3.12+ - Backend workspace: API (`backend/api/`), shared core (`backend/core/`), Celery scheduler (`backend/scheduler/`). Pinned via `requires-python = ">=3.12"` in `backend/pyproject.toml`, `backend/core/pyproject.toml`, `backend/api/pyproject.toml`, `backend/scheduler/pyproject.toml`.
- TypeScript ~6.0 - Web dashboard (`frontend/dashboard/src/`).
- Kotlin 2.3.21 - Mobile app, Kotlin Multiplatform shared code (`frontend/mobile/`), declared in `frontend/mobile/gradle/libs.versions.toml`.

**Secondary:**
- Swift - iOS shell that hosts the KMP `Shared` framework (`frontend/mobile/iosApp/iosApp/iOSApp.swift`).
- Kotlin DSL (Gradle) - Build scripts across `frontend/mobile/` (`*.gradle.kts`).
- JavaScript (ESM) - Tooling config such as `frontend/dashboard/eslint.config.js` and `frontend/dashboard/prettier.config.js`.
- HTML/CSS - Dashboard entry `frontend/dashboard/index.html`, styles driven by Tailwind CSS 4 (`frontend/dashboard/src/styles/globals.css`).

## Runtime

**Backend environment:**
- CPython 3.12 (container base `python:3.12-slim-bookworm`, builder `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`), defined in `backend/Dockerfile`.
- Uvicorn runs the API with 2 workers: `CMD ["uvicorn", "openwellness_api.main:app", ..., "--workers", "2"]` in `backend/Dockerfile`.
- Celery worker runs the scheduler: `celery -A openwellness_scheduler worker -l info` in `backend/Dockerfile`.

**Frontend environment:**
- Node.js `^20.19.0 || ^22.12.0 || >=24.0.0` (engine constraint recorded in `frontend/dashboard/package-lock.json`). No `.nvmrc` or `.node-version` file is present.

**Mobile environment:**
- JVM target 11 for Android library compilation (`frontend/mobile/shared/build.gradle.kts`).
- Android `compileSdk`/`targetSdk` 36, `minSdk` 24 (`frontend/mobile/gradle/libs.versions.toml`).
- iOS targets `iosArm64` and `iosSimulatorArm64` (`frontend/mobile/shared/build.gradle.kts`).

**Package Managers:**
- Python: `uv` workspace (`[tool.uv.workspace]` in `backend/pyproject.toml`). Lockfile present: `backend/uv.lock`. Installed with `uv sync --frozen` in `backend/Dockerfile`.
- Node: npm. Lockfile present: `frontend/dashboard/package-lock.json`.
- Gradle: Gradle wrapper scripts present (`frontend/mobile/gradlew`, `frontend/mobile/gradlew.bat`). Gradle version pinned in `frontend/mobile/gradle/gradle-daemon-jvm.properties`. No separate lockfile detected.

## Frameworks

**Backend core:**
- FastAPI (locked 0.136.3) - HTTP API. App factory in `backend/api/src/openwellness_api/main.py`, v1 router in `backend/api/src/openwellness_api/v1.py`.
- Pydantic 2 (locked 2.13.4) and pydantic-settings (>=2.3) - Request/response schemas (`backend/api/src/openwellness_api/schemas/`) and env-driven config (`backend/api/src/openwellness_api/config.py`).
- dependency-injector (locked 4.49.0) - DI containers: `backend/core/src/openwellness_core/infrastructure/containers/`, `backend/api/src/openwellness_api/container.py`, `backend/api/src/openwellness_api/deps/auth_container.py`, `backend/scheduler/src/openwellness_scheduler/container.py`.
- Celery (locked 5.6.3) - Background task worker, `backend/scheduler/src/openwellness_scheduler/infrastructure/celery_app.py`.
- Uvicorn (locked 0.48.0, `uvicorn[standard]`) - ASGI server.
- Arrow (locked 1.4.0) - Date/time handling in core.

**Backend testing:**
- pytest >=8 - Test runner across `backend/api/tests/`, `backend/core/tests/`, `backend/scheduler/tests/`.
- httpx >=0.27 - FastAPI test client transport (dev extra in `backend/api/pyproject.toml`).
- fakeredis >=2.20 - In-memory Redis for tests (dev extra in `backend/api/pyproject.toml`).
- mongomock >=4 - In-memory Mongo for tests (dev extra in `backend/api/pyproject.toml`).
- time-machine >=2.13 - Clock control in tests (dev extra in `backend/api/pyproject.toml`).
- pyright >=1.1 - Static type checking; config in `backend/pyrightconfig.json`.

**Frontend (dashboard):**
- React 19.2 (locked 19.2.7) and react-dom - UI, `frontend/dashboard/package.json`.
- React Router 7.16 (`react-router-dom`) - Routing.
- TanStack React Query 5.101 (`@tanstack/react-query`) - Server-state fetching.
- Radix UI 1.4 (`radix-ui`) and shadcn-style config (`frontend/dashboard/components.json`) - Component primitives.
- Tailwind CSS 4.3 with `@tailwindcss/vite` plugin - Styling, configured via `frontend/dashboard/vite.config.ts`.
- class-variance-authority, clsx, tailwind-merge, lucide-react - Styling and icon utilities.

**Frontend testing:**
- Vitest 4.1 (locked 4.1.8) - Runner. Config is in `frontend/dashboard/vite.config.ts` (`test` block, jsdom environment, setup file `./src/test/setup.ts`).
- Testing Library (`@testing-library/react` 16.3, `@testing-library/jest-dom` 6.9, `@testing-library/user-event` 14.6) - Component tests.
- jsdom 29.1 - DOM environment.
- MSW 2.14 (`msw`) - Network mocking.

**Frontend build/dev:**
- Vite 8.0 (locked 8.0.16) - Dev server and bundler, `frontend/dashboard/vite.config.ts`.
- @vitejs/plugin-react 6.0 - React Fast Refresh and JSX.
- TypeScript 6.0 (locked 6.0.3) - Type checking via `tsc -b` (`frontend/dashboard/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`).
- ESLint 10 with `typescript-eslint` 8.59, `eslint-plugin-react-hooks` 7.1, `eslint-plugin-react-refresh` 0.5, `eslint-plugin-import-x` 4.16 - Lint, config in `frontend/dashboard/eslint.config.js`.
- Prettier 3.8 with `prettier-plugin-tailwindcss` 0.8 - Formatting, config in `frontend/dashboard/prettier.config.js`.

**Mobile (KMP / Compose Multiplatform):**
- Kotlin 2.3.21 (`kotlin` in `frontend/mobile/gradle/libs.versions.toml`).
- Compose Multiplatform 1.11.0 (`composeMultiplatform`) with Material3 1.11.0-alpha07.
- Android Gradle Plugin 9.0.1 (`agp`).
- Koin 4.1.0 - DI (`koin-core`, `koin-compose`, `koin-compose-viewmodel`, `koin-android`).
- Ktor 3.5.0 - HTTP client with engines OkHttp (Android, `ktor-client-okhttp`) and Darwin (iOS, `ktor-client-darwin`); `Auth` bearer plugin for token refresh.
- kotlinx-serialization-json 1.10.0, kotlinx-coroutines 1.10.2, kotlinx-collections-immutable 0.4.0.
- Navigation Compose 2.9.2 (`navigation-compose`) - Type-safe navigation.
- AndroidX DataStore 1.2.1 (`datastore-preferences-core`, `datastore-core`) - Token persistence.
- AndroidX Lifecycle 2.11.0-beta01, Activity 1.13.0, AppCompat 1.7.1.
- Testing: kotlin-test, JUnit 4.13.2, Turbine 1.2.1, assertk 0.28.1, kotlinx-coroutines-test, Espresso 3.7.0.

**Build/Dev tooling (backend):**
- hatchling - Build backend for every workspace member (`[build-system]` in each `pyproject.toml`).

## Key Dependencies

**Backend - critical:**
- `couchbase` (locked 4.6.1, `>=4.2`) - Couchbase SDK. Cluster client and N1QL queries in `backend/core/src/openwellness_core/infrastructure/drivers/cb_entity_repository.py`.
- `pymongo` (locked 4.13.2, constrained `>=4.7,<4.14`) - MongoDB driver. Pin is deliberate: `backend/core/pyproject.toml` notes 4.14 drops MongoDB 4.0 support and staging Mongo is 4.0.x.
- `requests` (locked 2.34.2) - Sync Gateway HTTP client used by `CBEntityRepository` in `backend/core/src/openwellness_core/infrastructure/drivers/cb_entity_repository.py`.
- `redis` (locked 5.3.1, `>=5,<6`) - Redis client for OTP storage and rate limits, `backend/api/src/openwellness_api/deps/auth_container.py`, `backend/api/src/openwellness_api/auth/otp_store.py`.
- `pyjwt[crypto]` (locked 2.13.0, `>=2.9,<3`) - HS256 access tokens, `backend/api/src/openwellness_api/auth/token_service.py`.
- `email-validator` (`>=2,<3`) - Email field validation in API schemas.
- `python-multipart` (`>=0.0.9`) - Form parsing for FastAPI.
- `dependency-injector` (locked 4.49.0) - Composition root for all three backend services.
- `arrow` (locked 1.4.0) - Time-zone aware date handling in core.

**Backend - infrastructure / stdlib:**
- `smtplib` (stdlib) - Outbound OTP email via STARTTLS, `backend/api/src/openwellness_api/auth/email_sender.py`. No third-party mail SDK.
- `hashlib`, `secrets`, `hmac` (stdlib) - Refresh-token hashing and OTP handling.
- `celery` 5.4+ with `shared_task` decorators, `backend/scheduler/src/openwellness_scheduler/infrastructure/tasks.py`.

**Backend - dev only:** `httpx`, `pytest`, `pyright`, `fakeredis`, `time-machine`, `mongomock` (see Frameworks).

**Frontend - critical:**
- `@tanstack/react-query` 5.101 - Server state. Used with the API client in `frontend/dashboard/src/core/api/apiClient.ts`.
- `react-router-dom` 7.16 - Routing.
- `radix-ui` 1.4.3 - Accessible primitives.

**Mobile - critical:**
- `io.ktor:ktor-client-core` 3.5.0 with `ktor-client-auth` (bearer refresh) and `ktor-serialization-kotlinx-json`.
- `io.insert-koin` 4.1.0 - Shared DI graph bootstrapped by `initKoin(baseUrl)` / `doInitKoin(baseUrl:)`.

**Infrastructure:**
- Redis 7 - Container image `redis:7-alpine` in `docker-compose.yml`. Used as both OTP/rate-limit store (`REDIS_URL`) and Celery broker/result backend (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
- Couchbase Server with Sync Gateway - External instance, not containerized in this repo (see `.env.example`).
- MongoDB - External instance published on the VM host, reached via `host.docker.internal` (`.env.example`).

## Configuration

**Environment:**
- Backend settings are read from environment variables by pydantic-settings classes. Each class has an `env_prefix`:
  - `backend/api/src/openwellness_api/config.py`: `API_` (`APISettings`), `API_AUTH_` (`AuthSettings`), `SMTP_`, `REDIS_`, `COUCHBASE_`, `SYNC_GATEWAY_`, `MONGO_`.
  - `backend/scheduler/src/openwellness_scheduler/config.py`: `CELERY_` (`CelerySettings`), plus the shared `COUCHBASE_`, `SYNC_GATEWAY_`, `MONGO_` settings.
  - `backend/core/src/openwellness_core/infrastructure/config/app_config.py` defines the protocol-typed slices (`CouchbaseConfig`, `SyncGatewayConfig`, `MongoConfig`) that the services implement.
- Compose loads `.env` into both `api` and `scheduler` via `env_file: .env` (`docker-compose.yml`).
- Template for required variables: `.env.example` at repo root. Copy to `.env` on the target VM. `.env` is git-ignored (`.gitignore`).
- Key variables: `COUCHBASE_URL`, `COUCHBASE_USERNAME`, `COUCHBASE_PASSWORD`, `COUCHBASE_BUCKET_NAME`, `MONGO_URL`, `MONGO_DB`, `SYNC_GATEWAY_URL`, `API_TITLE`, `APP_STORE_ID`, `APP_IOS_BUNDLE_ID`, `APP_ONE_SIGNAL_APP_ID`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
- Auth-specific variables (`API_AUTH_*`) include `API_AUTH_JWT_SECRET`, `API_AUTH_CODE_PEPPER` (both must be at least 32 characters, enforced in the lifespan boot guard in `backend/api/src/openwellness_api/main.py`), `API_AUTH_REFRESH_COLLECTION`, `API_CORS_ALLOWED_ORIGINS`.
- Code-level defaults exist for local development (for example `COUCHBASE_PASSWORD` defaults to `password` and `MONGO_URL` to `mongodb://localhost:27017` in `backend/api/src/openwellness_api/config.py`). Production values must be supplied through the environment.
- Dashboard reads `VITE_API_BASE_URL` (inlined at build time), defaulting to `http://127.0.0.1:8000/v1` in `frontend/dashboard/src/core/api/env.ts`. Template: `frontend/dashboard/.env.example`.
- Mobile reads the API base URL from Gradle property into `BuildConfig.API_BASE_URL` (`frontend/mobile/androidApp/build.gradle.kts`) and from the Swift entry point `frontend/mobile/iosApp/iosApp/iOSApp.swift` (currently hardcoded to `http://localhost:8000/v1/`).

**Build:**
- Backend: `backend/Dockerfile` (multi-stage: `api` and `scheduler` targets), `backend/.dockerignore`, workspace `backend/pyproject.toml`, lock `backend/uv.lock`.
- Dashboard: `frontend/dashboard/vite.config.ts`, `frontend/dashboard/tsconfig*.json`, `frontend/dashboard/eslint.config.js`, `frontend/dashboard/prettier.config.js`, `frontend/dashboard/components.json`.
- Mobile: `frontend/mobile/settings.gradle.kts`, `frontend/mobile/build.gradle.kts`, `frontend/mobile/gradle/libs.versions.toml` (version catalog), `frontend/mobile/gradle.properties`.
- Compose: `docker-compose.yml` (services `api`, `redis`, `scheduler`; a comment notes dashboard and mobile-web services are planned).
- Lint guard: `backend/core/scripts/check_no_fstring_n1ql.py` enforces parameterized N1QL.

## Platform Requirements

**Development:**
- Python 3.12+ with `uv`.
- Node.js 20.19+ / 22.12+ / 24+ for the dashboard.
- JDK and Android Studio / Xcode for the mobile app (Gradle daemon JVM is configured by `frontend/mobile/gradle/gradle-daemon-jvm.properties`).
- Local Couchbase, Sync Gateway, and MongoDB instances, or pointers to shared ones via `.env`.
- Redis 7 for OTP and Celery (provided by `docker-compose.yml`).

**Production:**
- Docker Compose on a single VM (`docker-compose.yml`), with `restart: unless-stopped` on all services.
- API port bound to `127.0.0.1:8200` on the host (tunnel-only) and mapped to container port 8000.
- Couchbase and Sync Gateway reached over outbound network access; MongoDB reached via `host.docker.internal` through `extra_hosts: host-gateway`.
- Container user is non-root (`app`, UID 1000) in both backend images.

---

*Stack analysis: 2026-10-29*
