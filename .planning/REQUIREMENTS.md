# Requirements: OpenWellness — Self-Hostable on Postgres

**Defined:** 2026-10-29
**Core Value:** Someone who has never seen the codebase can clone the repo, follow the docs, and end up with a secured, working OpenWellness instance (Postgres-backed, offline-sync capable) that participants' phones and the coach dashboard can use.

## v1 Requirements

### Foundations

- [x] **FOUND-01**: CI runs all backend suites (core, api, scheduler), pyright, and dashboard lint/typecheck/test/format and mobile host tests on every PR
- [x] **FOUND-02**: Datastore and shared settings (Postgres, legacy Couchbase/Mongo, Redis) are defined once in `core` and consumed by both api and scheduler
- [x] **FOUND-03**: Services load settings from a `.env` file when run directly (uvicorn/celery) as well as under docker compose, from one documented location
- [x] **FOUND-04**: Domain entities carry no datastore-specific types (`bson.ObjectId` removed from domain; coercion lives in the Mongo adapter)
- [x] **FOUND-05**: Auth persistence (users-by-email lookup, refresh sessions) goes through repository ports instead of direct pymongo / Mongo-dict queries
- [x] **FOUND-06**: Repository errors are not swallowed — malformed ids map to not-found, datastore outages surface as 5xx and are logged via `logging` (no `print`)
- [x] **FOUND-07**: ADRs recorded for id format, timestamp representation, soft-delete semantics, token format, `owner` semantics, and the per-resource authorization policy table

### Authentication & Authorization

- [ ] **AUTH-01**: Every `/v1` route except `/v1/auth:*` and `/healthz` rejects requests without a valid bearer token with 401 (deny-by-default at the router; `enforce_principal` flag removed)
- [ ] **AUTH-02**: A test enumerates every registered route and asserts anonymous access returns 401
- [ ] **AUTH-03**: A participant can only read and write resources under their own `{user}`; another user's resources return 404 (including via `filter=`)
- [ ] **AUTH-04**: Admin resources and the user list require the `admin` role (403 otherwise)
- [ ] **AUTH-05**: Coach-facing endpoints require the `coach` or `admin` role, and a coach reads or writes only records whose study id is in their `coach_studies` claim, with every write also checked against the target owner's Participant record (ADRs 0006 and 0007); a record or participant in any other study returns 404; this absorbs the former v2 AUTHZ-01 (D-02)
- [ ] **AUTH-06**: Audit fields (`updated_by`, etc.) come only from the verified token; the `X-Principal-Id` header is ignored
- [ ] **AUTH-07**: Access tokens carry a `kid` header and are signed with an asymmetric key (EdDSA default); the API publishes a JWKS endpoint
- [ ] **AUTH-08**: Concurrent refresh with the same refresh token within a short grace window does not trigger reuse-detection logout
- [ ] **AUTH-09**: Dashboard and mobile clients keep working end to end against the enforced API

### Postgres Datastore

- [ ] **PG-01**: Postgres adapters implement every persisted repository port (users, studies, participants, apps, devices, messages, weights, goals, wearable records, etc., per entity triage)
- [ ] **PG-02**: Versioned Alembic migrations create the full schema on an empty database; a one-shot `migrate` command applies them (never per-worker)
- [ ] **PG-03**: `DATASTORE_BACKEND=postgres|legacy` selects the backend at the composition root; Postgres is the default and imports no Couchbase/Mongo code; legacy drivers are an optional install extra
- [ ] **PG-04**: OTP login, registration, refresh and revoke work on Postgres (refresh sessions in Postgres with atomic rotation and scheduled expiry cleanup)
- [ ] **PG-05**: Soft delete semantics hold on Postgres: `DELETE` archives, `:undelete` restores, `:purge` hard-deletes, archived rows excluded from reads by default
- [ ] **PG-06**: List pagination is deterministic (stable ordering) and `filter=` behaves identically to the legacy backend
- [ ] **PG-07**: A shared repository contract test suite runs against the in-memory fakes always and against containerized Postgres under an `integration` marker
- [ ] **PG-08**: The legacy (Couchbase/Mongo) backend still boots and passes a smoke test when selected; docs state it does not support offline sync

### Sync Backend (PowerSync)

- [ ] **SYNC-01**: A self-hosted PowerSync service replicates from Postgres via an explicit `powersync` publication listing only synced tables (no auth/session/audit tables)
- [ ] **SYNC-02**: Sync Streams scope every synced row to the authenticated participant using only signed token claims; archived rows are not synced
- [ ] **SYNC-03**: A participant obtains sync credentials from an authenticated API endpoint that mints a short-lived token with `aud=powersync` and `kid`, verified by PowerSync via JWKS
- [ ] **SYNC-04**: A two-participant isolation test proves neither device receives the other's data
- [ ] **SYNC-05**: Offline-writable resources accept a client-supplied id and optional client `createTime`; replayed creates are idempotent
- [ ] **SYNC-06**: Data written on the server (including Fitbit/ActiGraph wearable records) reaches the owning participant's device; wearable tables are download-only
- [ ] **SYNC-07**: Full wearable history syncs; a load test with 90 days of synthetic minute-level wearable data meets agreed initial-sync time and device-storage limits (if not, the carve-out is recorded and windowing applied)
- [ ] **SYNC-08**: Replication-slot WAL retention is capped and a monitoring check reports slot lag
- [ ] **SYNC-09**: One manifest defines synced tables (scope, writability, API path) and generates the publication, sync streams config, and mobile schema; CI fails on drift

### Mobile Offline Client

- [ ] **MOB-01**: The mobile app keeps a local database of all participant-scoped data, readable while offline
- [ ] **MOB-02**: A participant can create, edit and delete their data offline; changes upload through `/v1` when connectivity returns
- [ ] **MOB-03**: Permanent upload rejections (4xx) are recorded and surfaced without blocking the queue; transient failures (network/5xx) retry
- [ ] **MOB-04**: Data created on another device or on the server appears on the participant's device after sync
- [ ] **MOB-05**: A single token provider serves both the API client and the sync connector (no concurrent refresh races)
- [ ] **MOB-06**: Logout warns about pending uploads, then clears the local database
- [ ] **MOB-07**: The local database is excluded from OS backups (Android Auto Backup, iCloud)
- [ ] **MOB-08**: The app shows sync status (connected, syncing, pending uploads, last synced)
- [ ] **MOB-09**: Android and iOS dev builds can be pointed at any self-hosted server via documented configuration (no hardcoded localhost on iOS)

### Self-Host Kit

- [ ] **KIT-01**: `docker compose up` brings up api, scheduler worker, a single beat, Redis, Postgres, PowerSync, dashboard and (dev profile) Mailpit, with healthchecks and ordered startup behind the one-shot migrate
- [ ] **KIT-02**: All images pinned; no datastore, Redis or mail ports published beyond `127.0.0.1`; Redis requires a password
- [ ] **KIT-03**: `.env.example` lists every required variable with placeholders; the boot guard rejects placeholder, default, or short secrets
- [ ] **KIT-04**: A `generate-secrets` command writes a `.env` with strong random secrets and keys
- [ ] **KIT-05**: A `doctor` command checks configuration and connectivity (Postgres, Redis, SMTP, PowerSync, JWKS) and reports actionable failures
- [ ] **KIT-06**: An idempotent `bootstrap` CLI creates the first admin (no default credentials, no pre-auth setup endpoint); `--demo` seeds a coach, study and participant and refuses to run in production mode
- [ ] **KIT-07**: In dev, OTP emails are captured by Mailpit so login works without real SMTP
- [ ] **KIT-08**: An append-only audit table records who changed what (actor, action, resource, time) and is never synced to devices
- [ ] **KIT-09**: CI executes the README quickstart on a clean runner: compose up, bootstrap, OTP login via Mailpit API, authenticated API call, sync smoke

### Documentation

- [ ] **DOCS-01**: Root README quick start works verbatim on a fresh clone (verified by KIT-09)
- [ ] **DOCS-02**: A single-VM production guide covers reverse proxy/TLS (Caddy, sync-route buffering/timeouts), real SMTP over TLS, secrets, CORS, firewall, and upgrades
- [ ] **DOCS-03**: Backup and restore are documented and the restore procedure has been drilled on a clean machine (including PowerSync re-replication)
- [ ] **DOCS-04**: Dashboard production build and hosting documented (`VITE_API_BASE_URL` at build time, CORS origin match)
- [ ] **DOCS-05**: A configuration reference lists every variable, generated from the settings classes and checked in CI
- [ ] **DOCS-06**: Existing README inaccuracies fixed (refresh-session store, `uv sync` vs `--extra dev`, missing `API_AUTH_*`/`REDIS_*`/`SMTP_*`, scheduler beat)
- [ ] **DOCS-07**: A compliance-responsibilities page and hardening checklist explain what the operator must do for HIPAA/IRB contexts (no compliance claim)
- [ ] **DOCS-08**: A replication-slot / sync operations runbook covers lag, WAL growth, and slot invalidation recovery
- [ ] **DOCS-09**: PowerSync Open Edition license terms recorded in NOTICE and docs

## v2 Requirements

### Authorization

- **AUTHZ-02**: Postgres row-level security as defense in depth

### Mobile

- **MOBR-01**: Release builds, signing, and store distribution
- **MOBR-02**: Push notifications (OneSignal) setup
- **MOBR-03**: Encrypted local database (SQLCipher)

### Platform

- **PLAT-01**: Prebuilt images published to a registry (GHCR)
- **PLAT-02**: SSO / OIDC login
- **PLAT-03**: Upgrade to PowerSync Kotlin SDK ≥1.15.2 with Kotlin 2.4 / Gradle 9.7 toolchain bump

## Out of Scope

| Feature | Reason |
|---------|--------|
| ETL from existing Couchbase/Mongo data | New instances start fresh; legacy data stays where it is |
| Removing legacy Couchbase/Mongo adapters | Kept behind a flag for existing deployments |
| Offline sync on the legacy backend | PowerSync requires Postgres |
| Dashboard offline sync | Offline is a participant (mobile) need |
| Kubernetes / multi-node / managed-cloud guides | Single-VM is the v1 production target |
| New participant-facing study features | Project is about the platform, not new study content |
| "HIPAA compliant" claim | Compliance depends on the operator; we document responsibilities instead |
| Direct client writes to Postgres | API stays the single authority for validation and authorization |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| FOUND-06 | Phase 1 | Complete |
| FOUND-07 | Phase 1 | Complete |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| AUTH-06 | Phase 2 | Pending |
| AUTH-07 | Phase 3 | Pending |
| AUTH-08 | Phase 3 | Pending |
| AUTH-09 | Phase 2 | Pending |
| PG-01 | Phase 5 | Pending |
| PG-02 | Phase 4 | Pending |
| PG-03 | Phase 5 | Pending |
| PG-04 | Phase 4 | Pending |
| PG-05 | Phase 4 | Pending |
| PG-06 | Phase 4 | Pending |
| PG-07 | Phase 4 | Pending |
| PG-08 | Phase 5 | Pending |
| SYNC-01 | Phase 6 | Pending |
| SYNC-02 | Phase 6 | Pending |
| SYNC-03 | Phase 6 | Pending |
| SYNC-04 | Phase 6 | Pending |
| SYNC-05 | Phase 7 | Pending |
| SYNC-06 | Phase 7 | Pending |
| SYNC-07 | Phase 7 | Pending |
| SYNC-08 | Phase 6 | Pending |
| SYNC-09 | Phase 6 | Pending |
| MOB-01 | Phase 8 | Pending |
| MOB-02 | Phase 9 | Pending |
| MOB-03 | Phase 9 | Pending |
| MOB-04 | Phase 8 | Pending |
| MOB-05 | Phase 8 | Pending |
| MOB-06 | Phase 9 | Pending |
| MOB-07 | Phase 8 | Pending |
| MOB-08 | Phase 8 | Pending |
| MOB-09 | Phase 8 | Pending |
| KIT-01 | Phase 10 | Pending |
| KIT-02 | Phase 10 | Pending |
| KIT-03 | Phase 10 | Pending |
| KIT-04 | Phase 11 | Pending |
| KIT-05 | Phase 11 | Pending |
| KIT-06 | Phase 11 | Pending |
| KIT-07 | Phase 10 | Pending |
| KIT-08 | Phase 11 | Pending |
| KIT-09 | Phase 11 | Pending |
| DOCS-01 | Phase 11 | Pending |
| DOCS-02 | Phase 12 | Pending |
| DOCS-03 | Phase 12 | Pending |
| DOCS-04 | Phase 12 | Pending |
| DOCS-05 | Phase 10 | Pending |
| DOCS-06 | Phase 11 | Pending |
| DOCS-07 | Phase 12 | Pending |
| DOCS-08 | Phase 12 | Pending |
| DOCS-09 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 60 total
- Mapped to phases: 60
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-29*
*Last updated: 2026-10-29 after roadmap creation (traceability mapped)*
