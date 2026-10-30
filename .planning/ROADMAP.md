# Roadmap: OpenWellness: Self-Hostable on Postgres

## Overview

The work starts by settling the ground every later phase stands on: CI on every PR, one settings source with `.env` loading, datastore-neutral ports, and ADRs for ids, timestamps, soft delete, tokens, `owner` and the authorization policy table. These decisions are cheap now and expensive once data exists. Auth enforcement then closes the open health-data surface with deny-by-default routes, owner binding and role gates, followed by asymmetric `kid`-signed tokens with a JWKS and a refresh grace window. Alongside the auth work, Postgres arrives behind the existing ports: first the migration mechanism, the generic repository and auth on Postgres, then every entity family with Postgres as the default and the legacy stores behind a flag. PowerSync is layered on top: a self-hosted service with participant-scoped streams and proven isolation, then the offline write path and server-ingested wearable data at realistic volume. The mobile app gains a local database, read side and sync status first, then offline writes and safe logout. The self-host kit hardens the compose stack and adds operator tooling plus a README quick start that CI executes. Production documentation comes last and describes only behavior that is enforced and tested: the single-VM guide, dashboard hosting, a drilled backup/restore, the sync operations runbook and the operator's compliance responsibilities.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundations & Architecture Decisions** - CI on every PR, settings consolidated in `core` with `.env` loading, datastore-neutral ports, honest repository errors, and the ADRs later phases build on
- [ ] **Phase 2: Route Authentication & Authorization** - Deny-by-default bearer auth on every `/v1` route, owner binding, admin/coach role gates, and audit fields taken only from the verified token
- [ ] **Phase 3: Token Signing & Refresh Hardening** - Asymmetric `kid`-signed access tokens with a published JWKS, and a refresh grace window that survives concurrent clients
- [ ] **Phase 4: Postgres Foundation & Auth on Postgres** - Alembic migrations with a one-shot `migrate`, a generic Postgres repository proven by a shared contract suite, and OTP login on Postgres
- [ ] **Phase 5: All Entities on Postgres by Default** - Postgres adapters for every persisted port, `DATASTORE_BACKEND` selection with Postgres as default, legacy Couchbase/Mongo behind a flag
- [ ] **Phase 6: Self-Hosted PowerSync & Participant-Scoped Sync** - PowerSync replicating an explicit publication, Sync Streams scoped by signed claims, a sync-credentials endpoint, proven isolation, manifest-driven config
- [ ] **Phase 7: Offline Write Path & Server-Ingested Data** - Idempotent client-id creates, download-only wearable sync, and full wearable history validated at realistic volume
- [ ] **Phase 8: Mobile Local Database & Sync Status** - The mobile app holds all participant data locally, readable offline, receives server-side changes, shows sync status, and points at any server
- [ ] **Phase 9: Mobile Offline Writes & Safe Logout** - Participants create, edit and delete data offline; uploads go through `/v1` with correct failure handling; logout warns, then wipes
- [ ] **Phase 10: One-Command Local Stack** - `docker compose up` brings up the full stack with healthchecks, pinned images, loopback-only ports, a strict secret guard, Mailpit, and a generated config reference
- [ ] **Phase 11: Operator Tooling & Verified Quickstart** - `generate-secrets`, `doctor`, `bootstrap`, an append-only audit table, and a corrected README quick start executed in CI
- [ ] **Phase 12: Production Deployment & Operations Docs** - Single-VM production guide, dashboard hosting, drilled backup/restore, sync operations runbook, and compliance responsibilities

## Phase Details

### Phase 1: Foundations & Architecture Decisions
**Goal**: Contributors work on a trustworthy baseline: CI guards every PR, settings live in one place and load from `.env`, persistence flows only through datastore-neutral ports, and the cross-cutting decisions are written down before any Postgres schema exists
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07
**Success Criteria** (what must be TRUE):
  1. Every pull request runs the core, api and scheduler suites, pyright, the dashboard lint/typecheck/test/format checks and the mobile host tests, and a failing check shows on the PR
  2. A developer running `uvicorn` or `celery` directly gets the same settings as under docker compose, loaded from one documented `.env` location, with datastore and Redis settings defined once in `core`
  3. OTP login, registration and refresh still work end to end after users-by-email lookup and refresh sessions move behind repository ports, and no domain entity imports `bson` or any other datastore type
  4. A request with a malformed resource id returns 404, and a datastore outage returns a 5xx with the error logged through `logging` instead of an empty result
  5. ADRs record the id format, timestamp representation, soft-delete semantics, token format, `owner` semantics and the per-resource authorization policy table
**Plans**: 6/11 plans executed

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — GitHub Actions CI on every PR (backend, dashboard, mobile host tests) plus nightly iOS; make the current tree green first
- [x] 01-02-PLAN.md — Datastore/Redis/Postgres settings defined once in core; one repo-root `.env` for compose and direct runs
- [x] 01-03-PLAN.md — Honest Mongo repository errors: malformed id gives 404, outage gives a logged 500
- [x] 01-07-PLAN.md — ADRs 0001-0004: id format, timestamps, soft delete/purge, token format

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-04-PLAN.md — Participant ids become plain strings in the domain; the Mongo adapter owns ObjectId coercion
- [x] 01-08-PLAN.md — ADR 0005: `owner` semantics from evidence (developer checkpoint)
- [ ] 01-10-PLAN.md — Document the repo-root `.env`; localhost values for direct runs, compose overrides for Redis hostnames

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 01-05-PLAN.md — `UserRepository.get_by_email` port and a datastore-neutral duplicate-key exception (409)
- [ ] 01-09-PLAN.md — ADRs 0006-0007: coach study scope and the per-resource authorization policy table; requirements aligned with D-02

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 01-06-PLAN.md — `RefreshSessionRepository` port with a Mongo adapter, proven by contract tests

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 01-11-PLAN.md — `RefreshSessionStore` on the port, composition-root wiring (collection name still configurable); API auth source free of pymongo
**UI hint**: no
**Research flag**: Standard refactor patterns, so skip research. The ADRs must settle `owner` semantics (user id vs participant id, confirmed from the legacy model and tests), archive/purge retention, and the coach authorization model (role gate in v1) before the auth, Postgres and sync phases are planned.

### Phase 2: Route Authentication & Authorization
**Goal**: No participant health data is reachable without a verified token, and every caller can reach only what their identity and role allow
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-09
**Success Criteria** (what must be TRUE):
  1. An anonymous request to any `/v1` route other than `/v1/auth:*` and `/healthz` returns 401, proven by a test that enumerates every registered route, and the `enforce_principal` flag no longer exists
  2. A participant can read and write resources under their own `{user}`, while another user's resources return 404, including when reached through `filter=`
  3. A non-admin gets 403 on admin resources and the user list, and a participant gets 403 on coach-facing endpoints that coaches and admins can use
  4. Audit fields such as `updated_by` record the token's identity even when a request sends a forged `X-Principal-Id` header
  5. A coach can sign in and work in the dashboard, and a participant can sign in and use the mobile app, end to end against the enforced API
**Plans**: TBD
**UI hint**: no
**Research flag**: Coach authorization needs a decision session, not a spike. In v1 it is a role gate, and per-study scoping is recorded as a documented limit (deferred to AUTHZ-01). Run a logging-only pass first to find dashboard or mobile calls that are currently unauthenticated, then switch to enforcement.

### Phase 3: Token Signing & Refresh Hardening
**Goal**: Other services can verify access tokens through a published JWKS without sharing any secret, and participants stay logged in when two clients refresh at the same moment
**Depends on**: Phase 2
**Requirements**: AUTH-07, AUTH-08
**Success Criteria** (what must be TRUE):
  1. Access tokens carry a `kid` header and are signed with an asymmetric key (EdDSA by default), and the API serves the matching public key at a JWKS endpoint
  2. A verifier holding only the JWKS URL can validate an API-issued token, and a token with an unknown `kid` is rejected
  3. Two refresh requests with the same refresh token inside the grace window both leave the user logged in, while reuse outside the window still revokes the session
  4. Dashboard and mobile sign-in keep working after the switch to asymmetric signing
**Plans**: TBD
**UI hint**: no

### Phase 4: Postgres Foundation & Auth on Postgres
**Goal**: A user can sign in to an instance whose auth data lives in Postgres, and one contract suite proves the shared Postgres repository behaves exactly like the existing ports
**Depends on**: Phase 1, Phase 3
**Requirements**: PG-02, PG-04, PG-05, PG-06, PG-07
**Success Criteria** (what must be TRUE):
  1. Running the one-shot `migrate` command against an empty Postgres database brings the schema to the Alembic head, and API or worker processes never run migrations themselves
  2. With auth persistence on Postgres, a user can register, log in with an emailed OTP, refresh with atomic rotation and revoke, and a scheduled cleanup removes expired refresh sessions
  3. For resources stored in Postgres, `DELETE` archives, `:undelete` restores, `:purge` hard-deletes, and archived rows are excluded from reads unless requested
  4. Paging through a Postgres-backed list returns every item exactly once in a stable order, and a given `filter=` expression returns the same results as on the legacy backend
  5. One repository contract suite passes against the in-memory fakes on every run and against containerized Postgres under the `integration` marker
**Plans**: TBD
**Research flag**: Standard patterns (SQLAlchemy 2.1 Core, psycopg 3, Alembic), so only a day-one Alembic and SQLAlchemy 2.1 smoke test. Prove the generic repository on the auth tables and a Weight pilot before rolling it out. The Postgres refresh-session store must honor the refresh grace window from the token-hardening phase; the contract suite should cover that.

### Phase 5: All Entities on Postgres by Default
**Goal**: A fresh install runs entirely on Postgres by default with every API resource persisted there, while existing Couchbase/Mongo deployments still boot behind a flag
**Depends on**: Phase 4
**Requirements**: PG-01, PG-03, PG-08
**Success Criteria** (what must be TRUE):
  1. Every persisted resource (users, studies, participants, apps, devices, messages, weights, goals, wearable records and the rest of the entity triage) can be created, read, updated, listed and deleted through `/v1` on a Postgres-only instance
  2. Running `migrate` on an empty database creates tables for every persisted entity, and the contract suite passes for all of them against Postgres
  3. A default install with no datastore setting runs on Postgres and imports no Couchbase or Mongo code, and the legacy drivers install only through an optional extra
  4. Setting `DATASTORE_BACKEND=legacy` boots against Couchbase/Mongo and passes a smoke test, and the docs state that the legacy backend does not support offline sync
**Plans**: TBD
**Research flag**: Standard patterns. Do the entity triage first (which of the ~41 ports are persisted; plan on about 37 tables), then roll out by entity family in batches. A provider-parity test keeps the Postgres and legacy containers exposing the same providers.

### Phase 6: Self-Hosted PowerSync & Participant-Scoped Sync
**Goal**: A participant's authenticated sync client receives exactly their own data, and nothing else, from a self-hosted PowerSync service replicating from Postgres
**Depends on**: Phase 3, Phase 5
**Requirements**: SYNC-01, SYNC-02, SYNC-03, SYNC-04, SYNC-08, SYNC-09, DOCS-09
**Success Criteria** (what must be TRUE):
  1. A self-hosted PowerSync service replicates from Postgres through an explicit `powersync` publication that lists only synced tables, with no auth, session or audit tables in it
  2. A signed-in participant gets a short-lived sync token (`aud=powersync`, with `kid`) from an authenticated API endpoint, PowerSync accepts it through the API's JWKS, and anonymous callers get 401
  3. A two-participant isolation test shows each sync client receives only its own participant's rows, scoped by signed token claims alone, and archived rows are not synced
  4. One manifest generates the publication, the sync streams config and the mobile schema, and CI fails when any generated artifact drifts from it
  5. Replication-slot WAL retention is capped, a monitoring check reports slot lag, and the PowerSync Open Edition license terms are recorded in NOTICE and the docs
**Plans**: TBD
**Research flag**: Needs research. Spikes to run first: Postgres bucket storage (Beta) on the same server, with a second postgres container as fallback; the JWK shape and a plain-HTTP `jwks_uri` on the compose network; whether rows are removed from the device when `deleted_at` changes (fallback: sync the flag); and `!env` support in the pinned 1.27.2 image. Also confirm the Functional Source License allows shipping PowerSync in the self-host kit.

### Phase 7: Offline Write Path & Server-Ingested Data
**Goal**: The API accepts writes that originated offline without duplicating them, and server-ingested wearable data, including full history, reaches the owning participant's device within agreed limits
**Depends on**: Phase 6
**Requirements**: SYNC-05, SYNC-06, SYNC-07
**Success Criteria** (what must be TRUE):
  1. Offline-writable resources accept a client-supplied id and an optional client `createTime`, and replaying the same create leaves exactly one record
  2. A Fitbit or ActiGraph record written on the server appears in the owning participant's sync client, and wearable tables are download-only (client writes to them are not accepted)
  3. A load test with 90 days of synthetic minute-level wearable data meets the agreed initial-sync time and device-storage limits, or the carve-out is recorded and windowed streams are in place
**Plans**: TBD
**Research flag**: Needs research: the client timestamp text format, bucket and parameter limits, and the windowing syntax for wearable streams. Agree on the initial-sync time and storage limits before running the load test.

### Phase 8: Mobile Local Database & Sync Status
**Goal**: Participants can see all their data on their phone with no connection, see changes made elsewhere arrive, and know the app's sync state, using dev builds pointed at any self-hosted server
**Depends on**: Phase 7
**Requirements**: MOB-01, MOB-04, MOB-05, MOB-07, MOB-08, MOB-09
**Success Criteria** (what must be TRUE):
  1. After signing in once, a participant can browse all of their participant-scoped data with the phone in airplane mode
  2. Data created on the server or on another device appears on the participant's phone after sync, without restarting the app
  3. The app shows sync status: connected, syncing, pending uploads and last synced time
  4. API calls and sync running together across an access-token expiry never log the participant out, because one token provider serves both
  5. Android and iOS dev builds can be pointed at any self-hosted server through documented configuration (no hardcoded localhost on iOS), and the local database is excluded from Android Auto Backup and iCloud backup
**Plans**: TBD
**UI hint**: yes
**Research flag**: Needs research. Run a toolchain spike first: PowerSync Kotlin SDK 1.14.1 under Gradle 9.1.0 / AGP 9.0.1, the iOS runtime, and coroutines/serialization alignment (avoid 1.15.0 and 1.15.1).

### Phase 9: Mobile Offline Writes & Safe Logout
**Goal**: Participants can create, edit and delete their data with no connection, rely on it reaching the server through `/v1` when they reconnect, and log out without silently losing or leaking data
**Depends on**: Phase 8
**Requirements**: MOB-02, MOB-03, MOB-06
**Success Criteria** (what must be TRUE):
  1. A participant can create, edit and delete their data in airplane mode, sees each change immediately, and the change reaches the server through `/v1` once connectivity returns
  2. Data written offline on one phone appears on a second phone signed in as the same participant after both sync
  3. A write the server permanently rejects (4xx) is recorded and shown to the participant without blocking later uploads, while network failures and 5xx responses retry automatically
  4. Logging out with pending uploads warns the participant first, and confirming the logout clears the local database so the next person to use the phone sees none of the previous participant's data
**Plans**: TBD
**UI hint**: yes
**Research flag**: Needs research: which PowerSync Kotlin SDK version fixed upload retry behavior, which determines the minimum SDK version and the error-classification approach.

### Phase 10: One-Command Local Stack
**Goal**: A contributor runs `docker compose up` on a fresh clone and gets the whole platform running, healthy and secure by default, with OTP emails caught locally
**Depends on**: Phase 6
**Requirements**: KIT-01, KIT-02, KIT-03, KIT-07, DOCS-05
**Success Criteria** (what must be TRUE):
  1. `docker compose up` starts the api, scheduler worker, a single beat, Redis, Postgres, PowerSync, the dashboard and (in the dev profile) Mailpit, with each service waiting on healthchecks and the one-shot migrate before it starts
  2. Every image is pinned to a version, no Postgres, Redis or mail port is published beyond `127.0.0.1`, and Redis rejects connections without its password
  3. `.env.example` lists every required variable with placeholders, and the API refuses to boot with a placeholder, default or too-short secret, naming the offending variable
  4. In the dev profile, a user who requests an OTP finds the email in Mailpit and can sign in with that code without any real SMTP server
  5. A configuration reference generated from the settings classes lists every variable, and CI fails when a setting changes without the reference being regenerated
**Plans**: TBD
**UI hint**: no
**Research flag**: Standard patterns (compose healthchecks, profiles, secret handling); the PowerSync compose sketch already exists in the research STACK.md.

### Phase 11: Operator Tooling & Verified Quickstart
**Goal**: Someone new to the codebase follows the README on a fresh clone to an instance with real secrets and a first admin they can log in as, and CI proves that path keeps working
**Depends on**: Phase 10
**Requirements**: KIT-04, KIT-05, KIT-06, KIT-08, KIT-09, DOCS-01, DOCS-06
**Success Criteria** (what must be TRUE):
  1. `generate-secrets` writes a `.env` with strong random secrets and signing keys that the boot guard accepts, and `doctor` checks Postgres, Redis, SMTP, PowerSync and JWKS and names each failure with an actionable fix
  2. `bootstrap` creates the first admin with no default credentials and no pre-auth setup endpoint, re-running it changes nothing, and `--demo` seeds a coach, study and participant but refuses to run in production mode
  3. Every create, update and delete through the API is recorded in an append-only audit table (actor, action, resource, time) that is never synced to devices
  4. The README quick start is corrected (refresh-session store, `uv sync` vs `--extra dev`, `API_AUTH_*`/`REDIS_*`/`SMTP_*`, scheduler beat) and works verbatim on a fresh clone
  5. CI runs the README quick start on a clean runner: compose up, bootstrap, OTP login through the Mailpit API, an authenticated API call and a sync smoke test
**Plans**: TBD

### Phase 12: Production Deployment & Operations Docs
**Goal**: An outside lab can use the docs alone to deploy a secured instance on one VM, host the dashboard, back it up and restore it, keep sync healthy, and understand its compliance responsibilities
**Depends on**: Phase 2, Phase 3, Phase 9, Phase 11
**Requirements**: DOCS-02, DOCS-03, DOCS-04, DOCS-07, DOCS-08
**Success Criteria** (what must be TRUE):
  1. Following the single-VM guide on a fresh VM yields an instance behind Caddy with TLS (sync route unbuffered with long timeouts), OTP mail over real SMTP with TLS, CORS set, only the intended ports open, and a documented upgrade path
  2. Building the dashboard with `VITE_API_BASE_URL` set at build time and hosting it as documented produces a dashboard that signs in against the production API with a matching CORS origin
  3. The documented backup and restore procedure has been drilled on a clean machine: the restored instance serves the same data and PowerSync re-replicates to devices
  4. An operator facing replication lag, WAL growth or slot invalidation can diagnose and recover by following the sync operations runbook
  5. A compliance-responsibilities document and hardening checklist explain what the operator must do in HIPAA/IRB contexts without claiming compliance
**Plans**: TBD
**UI hint**: no
**Research flag**: The compliance and backup posture is based on common practice, not sourced references; review the compliance document from an institutional security/IRB perspective before publishing. Include a WAL soak test (stop PowerSync and watch slot retention stay within the cap). This phase is the auth hard gate: it starts only after all AUTH-* requirements are complete.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

Declared dependencies allow parallel streams. Phase 4 waits for Phase 3 so the Postgres refresh store is built with the grace window, so phases 1–6 run in sequence. The kit stream (10 → 11) needs only Phase 6, so it can run alongside the write path and mobile (7 → 8 → 9). Phase 12 waits for everything.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundations & Architecture Decisions | 6/11 | In Progress | - |
| 2. Route Authentication & Authorization | 0/TBD | Not started | - |
| 3. Token Signing & Refresh Hardening | 0/TBD | Not started | - |
| 4. Postgres Foundation & Auth on Postgres | 0/TBD | Not started | - |
| 5. All Entities on Postgres by Default | 0/TBD | Not started | - |
| 6. Self-Hosted PowerSync & Participant-Scoped Sync | 0/TBD | Not started | - |
| 7. Offline Write Path & Server-Ingested Data | 0/TBD | Not started | - |
| 8. Mobile Local Database & Sync Status | 0/TBD | Not started | - |
| 9. Mobile Offline Writes & Safe Logout | 0/TBD | Not started | - |
| 10. One-Command Local Stack | 0/TBD | Not started | - |
| 11. Operator Tooling & Verified Quickstart | 0/TBD | Not started | - |
| 12. Production Deployment & Operations Docs | 0/TBD | Not started | - |
