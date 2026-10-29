# OpenWellness: Self-Hostable on Postgres

## What This Is

OpenWellness is an open-source, NIH-supported platform for running wellness research studies. Participants record wellness data in a mobile app, coaches and admins work from a web dashboard, and a Python backend owns the domain and the datastores. This project makes OpenWellness something an outside research lab (or a contributor) can actually stand up. It moves the backend off legacy Couchbase/Sync Gateway/MongoDB onto Postgres with PowerSync for offline-first mobile sync, closes the authentication gap, and ships a one-command self-host kit with accurate documentation, from a local dev stack through a single-VM production deployment and a mobile app pointed at it.

## Core Value

Someone who has never seen the codebase can clone the repo, follow the docs, and end up with a secured, working OpenWellness instance (Postgres-backed, offline-sync capable) that participants' phones and the coach dashboard can use, without needing knowledge that lives only in the original team's heads.

## Requirements

### Validated

<!-- Inferred from the existing codebase (.planning/codebase/). -->

- ✓ Clean Architecture Python uv workspace: shared `core` library (domain, repository ports, adapters, DI) consumed by sibling `api` and `scheduler` services — existing
- ✓ ~50 domain entities (users, studies, participants, weights, goals, Fitbit/ActiGraph records, messages, surveys, etc.) with repository ports (~41) and Couchbase/Mongo adapters — existing
- ✓ FastAPI service exposing entities as Google-AIP-style REST under `/v1` (resource names, standard methods, `:undelete`/`:purge`, cursor pagination, `filter=`, AIP-193 errors) — existing
- ✓ Email-OTP login/registration issuing rotating JWT access/refresh tokens, Redis-backed OTP + rate limits, SMTP delivery, 32-char secret boot guard — existing
- ✓ Celery scheduler with one sample use case (`count_study_participants`), DI container, Redis broker — existing
- ✓ React dashboard (Vite, React 19, Tailwind 4, shadcn/ui) with OTP login and coach/admin role gate — existing
- ✓ Compose Multiplatform mobile app (Android + iOS) with OTP login/registration, rotating-refresh Ktor client, DataStore token storage — existing
- ✓ Multi-stage backend Dockerfile (`api`, `scheduler` targets) and root `docker-compose.yml` (api, scheduler, redis) — existing
- ✓ Test suites for every package that run against in-memory fakes, no live infra needed — existing

### Active

**Security (must land before any production deployment docs):**
- [ ] All `/v1` resource routes require a verified bearer token (except `/v1/auth:*` and `/healthz`)
- [ ] Owner-scoped routes bind the token's subject/participant to the `{user}` path segment
- [ ] Admin routes and user listing require an admin role; coach capabilities gated by coach role
- [ ] Principal enforcement on by default; `X-Principal-Id` header no longer trusted for audit stamping

**Postgres migration:**
- [ ] Postgres adapters implementing the existing repository ports for all entities
- [ ] Postgres schema with migrations (versioned, reproducible on a fresh database)
- [ ] Datastore backend selectable by config; Postgres is the default; Couchbase/Mongo adapters retained behind the flag for existing deployments
- [ ] Refresh-session store and other auth persistence work on Postgres
- [ ] Shared settings (datastore config) consolidated into `core` instead of duplicated in api/scheduler

**Offline-first sync (PowerSync):**
- [ ] PowerSync service self-hosted against the Postgres instance, authenticated with the API's JWTs
- [ ] Sync rules scope each participant's device to that participant's data
- [ ] Mobile app keeps a local database of all participant-scoped data, readable and writable offline
- [ ] Offline writes upload through the API (server stays the authority for validation and auth)
- [ ] Data ingested on the server (e.g. Fitbit/ActiGraph wearable records) syncs down to the participant's device

**Self-host kit:**
- [ ] One-command local stack: `docker compose up` brings up api, scheduler (worker + beat), Redis, Postgres, PowerSync, dashboard, and a dev mail catcher
- [ ] Settings load from a documented `.env` file both under compose and when running services directly
- [ ] Complete `.env.example` covering every required variable (auth secrets, Redis, SMTP, Postgres, PowerSync, CORS) with secret-generation guidance
- [ ] Bootstrap/seed command creates the first admin (and optionally a demo coach, study, participant) so a fresh instance is loggable-into
- [ ] Dev mode where OTP emails are captured locally (no real SMTP needed)

**Documentation:**
- [ ] README quick start that actually works on a fresh clone, verified end to end
- [ ] Single deployment guide for one VM: TLS/reverse proxy, real SMTP, secrets, CORS, backups, upgrades
- [ ] Dashboard production build and hosting documented (build-time `VITE_API_BASE_URL`, CORS origin match)
- [ ] Mobile (Android + iOS) dev builds pointable at any self-hosted server via documented config, including the iOS URL (no hardcoded localhost)
- [ ] Every configuration variable documented in one reference table; existing README inaccuracies fixed (refresh-session store location, `uv sync` vs `--extra dev`, missing `API_AUTH_*`/`REDIS_*`/`SMTP_*`)

### Out of Scope

- ETL / data migration from existing Couchbase/Mongo deployments into Postgres — new instances start fresh; legacy data stays where it is
- Removing the Couchbase/Mongo adapters — kept behind a flag for existing deployments
- Mobile release builds, signing, app-store distribution, OneSignal push setup — v1 targets dev builds pointed at any server
- Dashboard offline-first sync — offline is a participant (mobile) need; dashboard stays online REST
- New participant-facing data-entry UI beyond what's needed to exercise synced data — this project is about the platform, not new study features
- Multi-node / Kubernetes / cloud-managed deployment guides — single-VM is the v1 production target
- Replacing the legacy production mobile app — the in-repo KMP app is the client this project builds on

## Context

- **Brownfield.** Codebase mapped 2026-10-29 in `.planning/codebase/` (ARCHITECTURE, STACK, CONCERNS, etc.). Clean Architecture is enforced by convention and tests; repository ports are the only persistence surface, which is what makes a Postgres adapter swap tractable.
- **Legacy production stack:** Couchbase + Sync Gateway + MongoDB. The legacy production mobile app is offline-first via Couchbase Lite + Sync Gateway; the in-repo KMP app is currently online-only and auth-only. PowerSync is intended to restore offline-first behavior on the new stack.
- **Sync Gateway in the current backend** is used only as a server-side HTTP document read/write path (unauthenticated requests, port 4984 default); N1QL queries go through the Couchbase SDK. Users/apps/devices/participants/studies/messages live in Mongo; most other entities in Couchbase.
- **README gap audit (2026-10-29)** found blockers: `.env` never loaded (no `env_file` in settings), required `API_AUTH_JWT_SECRET`/`API_AUTH_CODE_PEPPER` missing from `.env.example` and main docs (API refuses to boot), compose API's `REDIS_URL` defaults to container-local localhost; plus undocumented datastore provisioning, Sync Gateway auth, first-user bootstrap, SMTP, dashboard hosting, production hardening, and mobile server config.
- **Security concern (CONCERNS.md):** none of ~260 resource routes enforce auth; `require_principal` is dead code; `enforce_principal` defaults to false; admin routes have no role check. Health data is exposed to unauthenticated callers.
- **Scheduler** has no scheduled jobs and no beat process in compose.
- Funded by NIH (award in NOTICE); audience includes other research labs adopting the platform.

## Constraints

- **Architecture**: Postgres and PowerSync integrate as adapters behind existing `core` ports — domain and application layers stay datastore-agnostic (Dependency Rule)
- **Wire contract**: The AIP-style `/v1` API contract stays stable — dashboard and mobile clients depend on it
- **Security**: No production deployment documentation ships before route authentication is enforced — avoids inviting labs to expose participant health data
- **Sync tech**: PowerSync is the working choice; research validates fit (self-hosting, Kotlin Multiplatform SDK, Postgres replication, reuse of API JWTs) and only a hard blocker triggers reconsideration
- **Tests**: Existing suites keep running without live infrastructure; new Postgres work adds integration tests that can run against a containerized Postgres
- **Stack**: Python 3.12+/uv, FastAPI, Celery, React 19/Vite, Kotlin Multiplatform — no stack changes beyond adding Postgres, PowerSync, and a dev mail catcher
- **Compatibility**: Couchbase/Mongo deployments must keep working when the legacy datastore flag is selected

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Migrate to Postgres inside this project, before building the self-host kit | Building the kit on Couchbase/SG/Mongo would be thrown away; kit is built once on the target stack | — Pending |
| Fresh start, no ETL from legacy stores | No requirement to move existing production data into new instances | — Pending |
| Keep Couchbase/Mongo adapters behind a config flag | Existing deployments keep working during transition | — Pending |
| PowerSync for offline-first mobile sync, validated by research | Restores the Couchbase Lite + SG offline behavior on Postgres; supports server-ingested wearable data syncing down | — Pending |
| Sync full participant-scoped data in v1 (not a single slice) | Offline-first parity with the legacy app is the goal | — Pending |
| Enforce auth before writing production deployment docs | Unauthenticated routes expose health data | — Pending |
| Local-first kit, then single-VM production path, then mobile pointed at it | Serves contributors and outside labs; one-command local stack is the foundation | — Pending |
| Mobile scope = dev builds configurable to any server | Release/signing/distribution deferred | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-29 after initialization*
