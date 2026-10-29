# Project Research Summary

**Project:** OpenWellness: Self-Hostable on Postgres
**Domain:** Self-hostable research-study platform (Python FastAPI API with Clean Architecture, React dashboard, KMP mobile) moving from Couchbase/Sync Gateway/MongoDB to Postgres + PowerSync, with auth enforcement and a one-command self-host kit.
**Researched:** 2026-10-29
**Confidence:** MEDIUM-HIGH overall.

## Executive Summary

The product shape is settled. The API stays the only writer and owns validation and authorization. Postgres becomes the system of record behind the existing repository ports. PowerSync replicates Postgres to each participant's phone as a read-only stream. Offline writes return through the existing `/v1` REST API via the PowerSync upload queue. The stack is current and verified against official sources. Nothing in the research argues against PowerSync.

Two decisions carry most of the risk and must be made before any schema is written: (1) the id and timestamp strategy (PowerSync needs a text `id`; the domain uses str UUIDs and float epoch timestamps), and (2) the authorization model, because Sync Streams are a second authorization surface that must agree with API owner binding. Auth enforcement is a hard gate: today none of about 260 routes authenticate, so no production docs ship before deny-by-default is in place.

Main risks are security and operational: cross-participant leaks (IDOR, client-parameter-scoped streams, `FOR ALL TABLES` publication); replication slot filling the single-VM disk; upload-queue stalls from retryable errors on validation failures; refresh-token reuse detection logging users out when Ktor and the PowerSync connector refresh concurrently; a self-host kit shipping default secrets or published DB ports.

## Key Findings

### Recommended Stack

- **PostgreSQL 18** (`postgres:18`, volume at `/var/lib/postgresql`, `wal_level=logical`). HIGH.
- **SQLAlchemy 2.1 Core `>=2.1.6,<2.2`** (not ORM) + **psycopg 3 `[binary]` `>=3.3.6,<3.4`** (sync). HIGH.
- **Alembic `>=1.20.1,<1.21`**, run by a one-shot `migrate` service. MEDIUM-HIGH (spike against SA 2.1 on day one).
- **PowerSync Service `journeyapps/powersync-service:1.27.2`** (pin; never `latest`), `start -r unified`, Sync Streams `config: edition: 3`. HIGH.
- **PowerSync bucket storage on Postgres** (Beta) in a second database `powersync_storage` on the same server; fallback is a second postgres container. MEDIUM.
- **PowerSync Kotlin SDK `com.powersync:core` 1.14.1** (matches Kotlin 2.3.21, Compose MP 1.11.1, Ktor 3.5.0); plan bump to >=1.15.2 separately. Avoid 1.15.0/1.15.1. HIGH for versions.
- **Mailpit `axllent/mailpit:v1.32`** (dev SMTP catcher, REST API for scripted OTP login). HIGH.
- **testcontainers `>=4.15,<5`** with `PostgresContainer("postgres:18", driver="psycopg")`.
- **Tokens:** existing PyJWT plus `kid` and an asymmetric key (EdDSA default, RS256 alternative) published as JWKS. Mint a separate sync token with `aud=powersync`. Do not give PowerSync the API's HS256 secret.
- Avoid: `latest` tags, `FOR ALL TABLES`, Sync Rules (deprecated), `asyncpg`, psycopg2, MailHog, Supabase connector, direct client writes to Postgres.

### Expected Features

**Table stakes:**
- Deny-by-default bearer auth on `/v1` (allow-list `/v1/auth:*`, `/healthz`); owner binding of token subject to `{user}`; admin and coach role gates; `X-Principal-Id` trust removed; route-enumeration test expecting 401 anonymous on every route.
- Postgres adapters for all ~41 ports including refresh sessions; `DATASTORE_BACKEND=postgres|legacy` (Postgres default, no per-entity mixing).
- Settings consolidated in `core`; `.env` loaded under compose and direct runs; complete `.env.example`; boot guard rejects placeholder or short secrets.
- `docker compose up` with api, scheduler worker plus single beat, Redis, Postgres, PowerSync, dashboard, Mailpit; healthchecks; pinned tags; one-shot auto-migrate.
- Idempotent CLI first-admin bootstrap (no default creds, no pre-auth setup endpoint); optional demo seed behind an explicit flag.
- PowerSync: per-participant Sync Streams scoped by `auth.user_id()` or signed claim; explicit publication of synced tables only; wearable tables download-only; `uploadData()` through `/v1` with correct error semantics; wipe on logout.
- Single-VM prod guide (Caddy TLS, SMTP over TLS, secrets, CORS, tested backup/restore, upgrades, trusted proxy); dashboard hosting doc (`VITE_API_BASE_URL` baked at build); mobile server-URL config including iOS; config reference generated from settings classes.

**Differentiators (v1.x):** route policy registry plus authz parity test; append-only audit table (not in publication); `generate-secrets` and `doctor`; CI job executing the README quickstart; sync rejection channel; compose `dev` profile separated from prod.

**Defer (v2+):** coach-to-participant scoping beyond role gates (requirements decision); SQLCipher local DB encryption; Postgres RLS; SSO/OIDC; Kubernetes; mobile release builds; GHCR images; dashboard offline sync; ETL from legacy stores.

### Architecture Approach

Postgres adapters go behind unchanged `core` ports. A generic `PgBaseRepository[Entity]` mapper (dataclass to Table with codecs) plus thin per-entity subclasses avoids ~37 hand-written adapters. Backend selection at the composition root: current `RepositoryContainer` moves to `LegacyRepositoryContainer`, swapped in only for `DATASTORE_BACKEND=legacy`, so the default install imports no Couchbase/Mongo code. A parity test asserts both containers expose the same provider names. Auth enforcement applied once at router aggregation in `v1.py` via `require_principal`, with per-module `ACCESS` policy constants.

Mobile gets a `:core:sync` module (PowerSyncDatabase factory, generated Schema, `ApiBackendConnector`, sign-out wipe). Only `:core:sync` and `:feature:*:data` import PowerSync; feature domain stays pure Kotlin. A single `sync/manifest.yaml` (table, scope, writable, AIP collection/parent) generates sync config, publication SQL, Kotlin schema, and upload registry; CI fails on drift.

**Major components:**
1. `core/adapters/postgres` (new): Table definitions, generic mapper, base repos.
2. `core/infrastructure/containers` (changed): Postgres default; `bind_datastore()`; `PostgresLifecycle` verifies Alembic head.
3. `api/auth` (changed): `kid`, asymmetric signing, JWKS route, `RefreshSessionRepository` port, `auth:syncCredentials`.
4. `api/v1.py`, `deps/principal.py` (changed): router-level `require_principal`, `ACCESS` policies, owner binding (404 on mismatch, 403 on role failure).
5. PowerSync Service (new container): reads `powersync` publication, evaluates streams, storage in `powersync_storage`, verifies JWKS.
6. `sync/` manifest and generator (new).
7. Mobile `core:sync` (new): connector, schema, status, connect and disconnectAndClear lifecycle.
8. Mobile `feature:*:data`: `Local*Repository` over `db.watch()` and local `execute()`.

### Critical Pitfalls

1. **Auth per-route or behind a flag.** Prevent with one router-level deny-by-default dependency, delete the `enforce_principal` flag, route-enumeration test. Verify: anonymous call to each non-allow-listed route returns 401.
2. **Owner binding checks token, not relationship** (IDOR, hostile `filter=`, coach without study membership). Prevent with a written per-resource policy table, one owner helper, scope applied before user filter, two-user two-study tests.
3. **Sync scoped by client params or `FOR ALL TABLES`.** Prevent with `auth.user_id()` or signed-claim-only predicates, explicit `CREATE PUBLICATION powersync FOR TABLE ...` maintained in migrations, two-token isolation test as an exit gate.
4. **Shared HS256 secret / missing `kid` / wrong `aud` / localhost JWKS.** Prevent with a dedicated asymmetric sync token (`aud=powersync`, `kid`, 15-min TTL), JWKS on compose hostname, header and claims tests.
5. **Upload queue wedged by 4xx or swallowed errors.** Prevent with classification: 5xx and network throw (SDK retries); permanent 4xx recorded locally and `complete()`d; server applies writes synchronously before 2xx.
6. **Replication slot fills disk** (default `max_slot_wal_keep_size` unlimited). Prevent with explicit cap, `max_replication_slots` headroom, `pg_replication_slots` monitoring query, stop-PowerSync soak test.
7. **Refresh race between Ktor and PowerSync connector** trips reuse detection. Prevent with single-flight `TokenProvider` shared by both, plus a short server grace window.
8. **Init scripts only on empty volumes; migration races across workers.** Prevent with role/publication bootstrap plus Alembic in a one-shot `migrate` service that API and PowerSync wait on; CI runs empty DB, migrate, bootstrap, `powersync validate`.
9. **Default secrets and published ports in the kit.** Prevent with `127.0.0.1:` bindings or no publish, boot-guard denylist, generated `.env`, Redis `requirepass`, dev-only Mailpit profile.
10. **Port semantic drift in Postgres adapters** (non-deterministic pagination, float/timestamp round-trip, cast errors returning 500, copied Mongo `except: return None`). Prevent with shared contract suite on fakes and Postgres, `ORDER BY created_at, id`, specific exception mapping, timestamp/id ADR first.

## Implications for Roadmap

Seven phases (ordering matters more than numbering):

### Phase 1: Foundations and Architecture Decisions
**Rationale:** cheap now, expensive after data exists.
**Delivers:** CI (backend with fakes, frontend lint/test, N1QL lint); `CoreSettings` and `DatastoreSettings` in `core` with `.env` loading; `ObjectId` out of domain; `get_by_id(include_archived=...)`; `get_by_email`; `RefreshSessionRepository` port with Mongo adapter; container split with `bind_datastore`; remove dead config (`legacy_verified_id_salt`) and error swallowing in shared base code; ADRs for ids, timestamps, token format, soft delete, authorization policy table.

### Phase 2: Authentication and Authorization Enforcement
**Rationale:** PROJECT.md hard gate; independent of Postgres, can run parallel to Phase 3; must precede the PowerSync token endpoint.
**Delivers:** router-level deny-by-default; `ACCESS` per module; owner helper; role gates per ADR table; `X-Principal-Id` removed; `enforce_principal` deleted; route-enumeration 401 test and owner/wrong-role tests; logging-only pass first to find unauthenticated dashboard and mobile calls, then removed; `kid` and JWKS groundwork; trusted-proxy config; redacted structured logging.

### Phase 3: Postgres Datastore
**Delivers:** `pg_engine` and `PostgresLifecycle`; Core `MetaData`; generic mapper and base repos; Alembic baseline and `migrate`; `PgRefreshSessionRepository` with atomic `UPDATE ... RETURNING` and scheduled expiry cleanup; shared contract suite (fakes always, Postgres under `integration` marker); provider parity test; `alembic check`; deterministic ordering; `DATASTORE_BACKEND` default postgres with `legacy` extra. Order: engine, migrations, auth tables so OTP login works end to end, Weight pilot, remaining families in batches.

### Phase 4: PowerSync Backend and Offline Write Path
**Delivers:** PowerSync in compose with `service.yaml` (`!env`, `sslmode: disable` on private network only); `powersync_storage` DB; `powersync_role` (`REPLICATION BYPASSRLS`, `SELECT` on synced tables); publication generated from manifest; Sync Streams `edition: 3` with `auth.user_id()`/signed-claim predicates and `deleted_at IS NULL`; `auth:syncCredentials` minting 15-min `aud=powersync` token; JWKS on compose hostname; `max_slot_wal_keep_size` and slot monitoring; optional client-supplied id (`?weightId=`) with idempotent create and `createTime`; two-participant isolation test as exit gate; manifest generator with drift CI.

### Phase 5: Mobile Offline Client
**Delivers:** toolchain spike first; `:core:sync` with expect/actual driver factory, generated Schema, `ApiBackendConnector` (fetchCredentials via Ktor; uploadData maps PUT/PATCH/DELETE to `/v1`, DELETE to archive, 409 falls back to PATCH, error classification); single-flight `TokenProvider`; sync status flow; connect on login and start; `disconnectAndClear()` on logout with pending-upload warning; Android `allowBackup` exclusion and iOS backup exclusion; weights create/edit/delete offline round trip to a second device; then remaining participant data, with download-only wearable tables in bounded windows.

### Phase 6: Self-Host Kit
**Delivers:** compose healthchecks and `service_healthy`/`service_completed_successfully` ordering; single beat; `migrate` one-shot; `dev` profile (Mailpit, seed, exposed ports) vs prod; `127.0.0.1` bindings; Redis `requirepass` and AOF; full `.env.example` with `CHANGE_ME_*` placeholders; boot-guard denylist; `generate-secrets`; idempotent `bootstrap` CLI and `--demo` refusing production; OTP login via Mailpit API in CI; README quickstart executed in CI on clean runner.

### Phase 7: Production Documentation and Hardening
**Rationale:** Gated on Phase 2 per PROJECT.md.
**Delivers:** single-VM guide (Caddy, buffering off and long timeouts on sync route; SMTP over TLS; Postgres `sslmode=require` off-loopback; firewall and `ss -tlnp` check); config reference generated and CI-checked; dashboard hosting; mobile config for Android and iOS; backup script plus restore drill on a clean machine (secrets separately; bucket storage excluded as derived); replication-slot runbook; compliance responsibilities page (no "HIPAA compliant" claim); governance appendix; WAL soak test.

### Phase Ordering Rationale

Foundations first (cheap decisions); auth parallel to Postgres (different layers, both gate PowerSync); PowerSync backend before mobile (connector needs live token endpoint and pipeline); docs last (must describe enforced, tested behavior).

### Research Flags

- *Needs research-phase:* **Phase 4** (PowerSync spikes: same-server Beta storage; `oct` JWK shape and plain-HTTP `jwks_uri` in compose; remove-on-filter-transition for `deleted_at`; client timestamp text format; bucket and parameter limits and windowing syntax; `!env` in pinned version). **Phase 5** (Kotlin SDK 1.14.1 under Gradle 9.1.0 / AGP 9.0.1 and iOS runtime; which version fixed upload retry; Kotlin 2.4 bump; coroutines/serialization alignment). **Phase 2** coach-authorization is a decision session, not a spike. **Phase 7** compliance and backup posture is based on practice, not fetched sources; review with institutional security/IRB perspective.
- *Standard patterns, skip research:* **Phase 1** (refactors), **Phase 3** (SQLAlchemy Core, psycopg 3, Alembic; only a day-one smoke test), **Phase 6** (compose, profiles, secret generation; PowerSync compose sketch already in STACK.md).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Versions verified against registries and official PowerSync docs. Bucket storage on Postgres is Beta. 1.14.1 upload-retry behavior unknown. |
| Features | MEDIUM | PowerSync mechanics HIGH; peer comparisons MEDIUM/LOW (secondary summaries). |
| Architecture | MEDIUM-HIGH | Codebase read directly; container-swap seam verified experimentally. Soft-delete removal, device timestamp format, bucket limits are VERIFY. |
| Pitfalls | MEDIUM-HIGH | PowerSync pitfalls HIGH; Docker port, backup, compliance, OS backup MEDIUM (practice-based). |

**Overall confidence:** MEDIUM-HIGH

### Conflicts between research files (resolved)

1. **Token PowerSync receives.** Separate minted token (`aud=powersync`), not a copy of the API access token.
2. **Timestamps.** `double precision` epoch seconds (ratify in Phase 1 ADR); STACK preferred this, ARCHITECTURE suggested `timestamptz`.
3. **Primary key type.** `text` PK with UUID validation at repo boundary (malformed id returns 404, not 500).
4. **Soft delete on device.** Filter `deleted_at IS NULL` in streams; verify remove-on-transition in Phase 4 spike; fall back to flag sync if needed.
5. **Token algorithm.** EdDSA default, RS256 alternative.
6. **Table count.** Plan on ~37 persisted tables, pending entity triage in Phase 3.

### Gaps to Address

- **`owner` semantics** (user id vs participant id): confirm from legacy model and tests in Phase 1, before any stream predicate.
- **Coach authorization model** (role gate vs study membership): decide before Phase 2 planning; recommended default is role gate in v1, documented limit.
- **Archive/purge semantics** (restore window, retention): needed before Phase 3 soft-delete work.
- **PowerSync Open Edition license** (Functional Source License, not OSI): record in NOTICE and risk register; check kit redistribution before Phase 6.
- **Postgres bucket storage (Beta):** spike in Phase 4; fallback second container.
- **Kotlin toolchain:** verify 1.14.1 build and iOS runtime; confirm upload-retry fix version before choosing minimum.
- **Wearable sync volume:** load test with 90 days synthetic ActiGraph/Fitbit in Phase 4 or 5 before accepting "sync full participant-scoped data in v1"; if it fails, window those streams and record the carve-out.
- **Refresh grace window and reuse detection under concurrent refresh:** server-side test in Phase 2.
- **Compliance and backup posture:** review before publishing the Phase 7 compliance page.

## Sources

### Primary (HIGH confidence)
- docs.powersync.com (self-hosted instances, Postgres source setup, custom auth, Sync Streams overview/queries/parameters/bucket-count, writing client changes, conflict handling, Kotlin SDK reference, types, Postgres maintenance, production readiness)
- github.com/powersync-ja/powersync-kotlin (CHANGELOG, libs.versions.toml at tags); github.com/powersync-ja/self-host-demo
- Maven Central; Docker Hub; PyPI; SQLAlchemy 2.1 migration notes; Mailpit docs and v1.32.0; testcontainers-python; endoflife.date
- Local codebase files (auth/token_service.py, auth/session_store.py, auth/email_sender.py, main.py, v1.py, deps/principal.py, containers, resources, base entities, pagination.py, mobile libs.versions.toml, CONCERNS.md); dependency-injector experiment

### Secondary (MEDIUM confidence)
- PowerSync bucket-storage and deployment pages (partly search summaries); schema-change caveats; SQLDelight integration (beta)
- Peer docs (Immich, Plausible, Supabase, Cal.com, Mattermost, read via summaries)
- Docker port publishing vs firewall, Android/iOS backup behavior, proxy buffering for streams, HIPAA/IRB expectations (practice-based, not fetched)

### Tertiary (LOW confidence)
- REDCap, Beiwe, RADAR-base comparisons (search summaries, dated pages); expected operator behavior and sizing (measure in Phases 4 and 7)

---
*Research completed: 2026-10-29*
*Ready for roadmap: yes*
