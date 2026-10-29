# Pitfalls Research

**Domain:** Brownfield migration of a Clean Architecture Python backend (Couchbase/Mongo to Postgres, dual backend behind a flag), self-hosted PowerSync offline-first sync for a Kotlin Multiplatform app, auth enforcement on a previously open API, and a self-host kit for outside labs handling participant health data.
**Researched:** 2026-10-29
**Confidence:** MEDIUM-HIGH. PowerSync facts come from official docs fetched during this research (HIGH). Codebase-specific claims come from `.planning/codebase/CONCERNS.md` plus direct reads of `pagination.py`, `base_entity.py`, `base_owner_entity.py`, `token_service.py`, `config.py` (HIGH). Items marked "verify" are plausible from experience but not confirmed by a fetched source (MEDIUM/LOW).

**Phase labels used below** (the roadmapper may rename or renumber; the ordering is what matters):

| Label | Scope |
|-------|-------|
| P1 Foundations | CI, `.env` loading, settings consolidation into `core`, fix error swallowing |
| P2 Auth enforcement | Route auth, owner binding, role model, drop `X-Principal-Id` |
| P3 Postgres adapters | Schema, migrations, adapters behind the flag, refresh-session store |
| P4 PowerSync backend | PowerSync service, JWT/JWKS, sync config, upload endpoint |
| P5 Mobile offline client | KMP local DB, connector, token handling, logout semantics |
| P6 Self-host kit | Compose stack, `.env.example`, bootstrap/seed, mail catcher, beat |
| P7 Docs and prod guide | README, single-VM guide, config reference, backups, compliance posture |
| P8 Mobile server config | Dev builds pointed at any server (Android/iOS URLs, TLS) |

---

## Critical Pitfalls

### Pitfall 1: Auth "enforced" by flag or by per-route opt-in, leaving routes open

**What goes wrong:**
Auth is added to the routes someone remembered, or `enforce_principal` is flipped without a dependency on every router. With ~260 route decorators across ~50 resource modules, a new resource added later (or one of the 36 modules that import `get_principal` only for audit stamping) silently ships open. A related failure: leaving `enforce_principal` as an env-toggle whose default stays `False`, so a lab that copies a minimal `.env` is open by default.

**Why it happens:**
`require_principal` is currently dead code and permissive-by-design ("rollout mode"). The natural incremental fix is to sprinkle `Depends(require_principal)` per resource, or to rely on the flag. Both leave a "forgot one" failure mode, and nothing in the repo (no CI, no route-enumeration test) catches it.

**How to avoid:**
- Attach the strict auth dependency once, at the `/v1` router level in `build_v1_router()`, with an explicit allowlist (`/v1/auth:*`, `/healthz`). Deny-by-default.
- Delete the `enforce_principal` flag and the permissive code path instead of flipping its default. A flag that can be turned off will be turned off in some lab's `.env`.
- Add a test that enumerates `app.routes` (or the OpenAPI schema), and asserts 401 for an anonymous call to every non-allowlisted route, so any new route is covered automatically. CONCERNS.md lists this as a High-priority test gap.
- Make the test fail if a route is neither authenticated nor in the allowlist.

**Warning signs:**
- A route module that declares its own `Depends(get_principal)` but nothing at the router.
- `API_AUTH_ENFORCE_PRINCIPAL` appearing in `.env.example` or docs as something to "turn on".
- Test fixtures that build the app with permissive principal (current state of `test_users_crud.py`, `test_weights_owner_crud.py`).

**Phase to address:** P2 Auth enforcement (must precede P6/P7 production docs, per the PROJECT.md constraint).

---

### Pitfall 2: Owner binding that checks the token but not the relationship (IDOR, filter injection, coach over-reach)

**What goes wrong:**
A valid bearer token is required, but any logged-in participant can read `/v1/users/{other}/weights`; or a coach with `roles: ["coach"]` can read every study's participants; or the list `filter=` parameter overrides the owner scope (`filter=owner="someone-else"`), or non-owner-scoped resources (studies, messages, Fitbit records, devices, apps) have no `{user}` segment and therefore get *no* binding at all.

**Why it happens:**
The existing `check_parent` only returns 404 for cross-owner confusion between `{user}` and the entity; it is not an authorization check. "Add auth" gets implemented as "authenticated = authorized". The `roles` claim is parsed into `AccessClaims` but nothing consumes it. The role model has no source of truth in the code yet (admins and coaches are separate entities; there is no coach-to-study membership check). Roles inside a 15-minute JWT also go stale after a role change.

**How to avoid:**
- Write the authorization policy table before code: for each of the ~50 resources, who can list/get/create/patch/delete/undelete/purge (participant-self, coach-of-study, admin, none). Review it; it is the security spec.
- Participant-self: bind `sub`/`participant` claim to `{user}` and compare with a single helper used by every owner-scoped router. Return 403 (or 404 consistently) for mismatch, but pick one and test it.
- Coach: authorize by study membership (coach assigned to study X, participant enrolled in study X), not by role string alone.
- Admin routes (`resources/admin.py`) and `GET /v1/users` (list): admin role only.
- Apply owner/study scoping server-side *before* applying user-supplied `filter=`; never let the filter widen scope. Add a test with a hostile filter.
- Decide `:purge` / `:undelete` / DELETE policy explicitly (likely admin-only for purge; participants may archive their own).
- Resolve role from the datastore (or keep JWT TTL short and accept staleness knowingly); document which.

**Warning signs:**
- A policy implemented with `if "coach" in claims.roles` and no study check.
- Tests that only use one test user (cross-user access never exercised).
- Resource modules with no `{user}` path segment passing review without a stated policy.

**Phase to address:** P2 Auth enforcement.

---

### Pitfall 3: Auth rollout breaks the two existing clients and PowerSync's upload path

**What goes wrong:**
Enforcing auth makes the dashboard or mobile app start getting 401/403 on calls that previously worked unauthenticated (a call site that never attached the token, a prefetch before login, a mobile endpoint used before refresh completes). Separately, the new PowerSync upload endpoint is built outside the `/v1` router and ends up either unauthenticated or exempt from owner binding.

**Why it happens:**
Because nothing was enforced, clients were never forced to send tokens everywhere; "works today" masks missing headers. Internal callers (the scheduler, scripts) also hit repositories directly and are unaffected, which hides the gap.

**How to avoid:**
- Before flipping enforcement, run the dashboard and mobile against a build with logging-only 401s to find unauthenticated call sites (the existing permissive mode already logs would-be 401s; use those logs as a worklist, then delete the mode).
- Keep the wire contract (`/v1` AIP style, AIP-193 errors) stable for 401/403 bodies so clients' error handling works.
- Remove `X-Principal-Id` trust in the same change (CONCERNS.md); add a regression test that a forged header on an authenticated request is ignored and on an anonymous request yields 401.
- Route the PowerSync upload through the same dependency and policy layer (see Pitfall 8).

**Warning signs:**
- Dashboard network tab showing 401 on first load; mobile Ktor client calls made outside the authenticated client instance.
- Spike in 401s after deploy; support questions in the first day about "logged out".

**Phase to address:** P2 Auth enforcement (client verification), P4 for the upload path.

---

### Pitfall 4: Sharing the API's HS256 secret with PowerSync (and forgetting `kid`)

**What goes wrong:**
The API mints HS256 JWTs with `API_AUTH_JWT_SECRET` (`token_service.py`, `jwt_alg="HS256"`). The tempting shortcut is to put the same secret in PowerSync's `service.yaml` `client_auth`. That puts the token-minting key into a second service and its config, and PowerSync's own docs say HS256 is for dev/testing only. Separately, tokens without a `kid` header are rejected by PowerSync, and tokens must carry `iat`/`exp` with at most 24h between them. The API's current `aud` is `openwellness-api`; PowerSync must be configured with a matching `client_auth.audience`, or manual JWKS config errors out.

**Why it happens:**
It "works" in a 10-minute local demo. PyJWT does not emit `kid` unless you pass `headers={"kid": ...}`. The JWKS route has to be reachable from the PowerSync container, which people point at `localhost`.

**How to avoid:**
- Switch the API to an asymmetric algorithm (ES256 or EdDSA) with a key pair and `kid`, expose a public JWKS document, and point PowerSync's `jwks_uri` at it using the compose service hostname (not `localhost`). Keep HS256 only for local dev if at all.
- Alternative acceptable design: mint a *separate*, narrowly-scoped PowerSync token (own audience, own key) from an authenticated API endpoint, so the API token and sync token are not interchangeable.
- Cover with tests: token has `kid`, `aud` matches the PowerSync config, `exp - iat` is well under the limit (keep 15 minutes; PowerSync recommends 60 minutes or less).
- Document key rotation: add new key to JWKS, wait ~5 minutes (PowerSync polls), switch signing, wait out old tokens, remove old key.
- Understand that PowerSync tokens cannot be revoked before expiry except by rotating the signing key; this drives the short TTL.

**Warning signs:**
- The same env var appears in both the API and PowerSync config; PowerSync logs `kid` or `aud` mismatch errors; `jwks_uri: http://localhost:...` in a compose file.

**Phase to address:** P4 PowerSync backend (decision must be made before P2 finalizes token shape if the algorithm changes; flag for early ADR).

---

### Pitfall 5: Sync config that scopes by client-controlled parameters, or syncs more than a participant should see

**What goes wrong:**
Another participant's (or another study's) rows reach a device. Causes: a stream/bucket with no parameter (a single global bucket delivered to everyone); scoping on a *subscription or connection parameter* (client-controlled) rather than `auth.user_id()` / JWT claims; `OR` branches that widen the filter; study-level tables (study settings, study messages) keyed by `study_id` without verifying the participant's enrollment; and a publication created `FOR ALL TABLES`, which also streams `auth_refresh_sessions`, OTP-adjacent data, and user PII tables into PowerSync's bucket storage even if no stream exposes them.

**Why it happens:**
The sync rules are a second authorization layer that duplicates the API's policy, written in a different language and tested differently. Official docs describe only auth parameters (JWT claims) as tamper-proof; subscription and connection parameters are client-controlled. The docs also have an `accept_potentially_dangerous_queries` escape hatch that silences warnings.

**How to avoid:**
- Scope every stream by auth parameters only: `auth.user_id()` and, for study data, an enrollment lookup done in the stream's subquery (or a claim the server controls). Never trust a client-supplied participant or study id.
- Use an explicit publication listing only the tables that are synced (`CREATE PUBLICATION powersync FOR TABLE ...`, the publication must be named `powersync`), and manage it in migrations so a new table is not accidentally published. Never sync auth/session/OTP/admin tables.
- Do not set `accept_potentially_dangerous_queries`; treat any compiler warning as a build failure in CI (`powersync validate`).
- Write an automated isolation test as a P4 exit gate: two participants in two studies, each token fetches its stream, assert zero rows from the other. Re-run on every sync-config change.
- Sync to devices only what the *participant* may see; coach and admin views stay REST-only (matches PROJECT.md: dashboard stays online).
- Plan consent withdrawal: a participant removed from a study stops receiving new data, but already-synced rows stay on the device; define the wipe path (see Pitfall 12).

**Warning signs:**
- A stream definition with no `auth.*` reference; a `SELECT *` over a table that has columns the participant should not see (coach notes, internal flags); `FOR ALL TABLES` in any init script.

**Phase to address:** P4 PowerSync backend; policy review shared with P2.

---

### Pitfall 6: Replication slot / WAL growth fills the disk (including on dev laptops and the single VM)

**What goes wrong:**
PowerSync holds a logical replication slot. If the PowerSync container is stopped, crashes, or is removed while Postgres keeps running, Postgres retains WAL for the slot indefinitely. On a single-VM deployment the data volume fills and Postgres stops accepting writes (taking the API down, which for participants means failed uploads). The opposite failure: `max_slot_wal_keep_size` set too low invalidates the slot mid-initial-snapshot (`PSYNC_S1146`) and the service does not retry on its own. Also: each Sync Config deploy creates a second slot while reprocessing, so `max_replication_slots` must have headroom.

**Why it happens:**
Defaults: `max_slot_wal_keep_size = -1` (unlimited) so a dead consumer is unbounded; developers `docker compose stop powersync` and forget; orphaned slots survive container removal. Sizing for steady-state instead of initial replication (WAL growth during snapshots is much higher).

**How to avoid:**
- Set `max_slot_wal_keep_size` explicitly in the compose Postgres command (size to disk; leave a floor for initial snapshot) along with `wal_level=logical`, `max_replication_slots`, `max_wal_senders`.
- On Postgres 18+, also set `idle_replication_slot_timeout`.
- Ship a `doctor`/health script (and document the query) that lists `pg_replication_slots` with `active = false` and lag via `pg_wal_lsn_diff`; wire PowerSync's Diagnostics API into the deployment guide and alert on non-empty `errors`.
- Document the recovery runbook: increase the limit, drop the invalidated slot, restart PowerSync (it re-creates the slot and re-snapshots). Do not drop slots while reprocessing is running.
- Stopping the stack for good must include `docker compose down -v` or an explicit "drop slot" step in the docs.
- Disk monitoring on the data volume is part of the single-VM guide, not optional.

**Warning signs:**
- `pg_wal` directory growing; `pg_replication_slots.active = false`; snapshot "less than 50% of WAL budget" warning in PowerSync logs; error "all replication slots are in use".

**Phase to address:** P6 Self-host kit (settings), P7 Docs and prod guide (monitoring, runbook).

---

### Pitfall 7: Postgres container bootstrap that doesn't run on existing volumes, and migrations that diverge from replication grants

**What goes wrong:**
`wal_level=logical`, the `powersync_role` (`REPLICATION BYPASSRLS LOGIN`), `GRANT SELECT`, and the publication are put in `docker-entrypoint-initdb.d`. Those scripts only run on an empty data directory, so anyone with an existing volume (every contributor after their first run) gets a stack where PowerSync can't connect, and the failure is non-obvious. Later, Alembic migrations (run as the app role) add tables that the replication role has no `SELECT` on, or that are missing from an explicit publication, so new data silently never syncs. Updates/deletes against a *published* table without a primary key/replica identity fail on the Postgres side.

**Why it happens:**
Role/publication creation needs superuser; migrations run unprivileged; two different mechanisms own overlapping state.

**How to avoid:**
- Separate idempotent "database bootstrap" (superuser step: role, publication, settings) from "schema migrations" (app role). Run both from a one-shot `migrate` compose service before `api`, never from each of the 2 uvicorn workers' startup (race).
- Use `ALTER DEFAULT PRIVILEGES ... GRANT SELECT` for the replication role; add the publication change to the migration that adds a synced table (or a migration-time check that fails if a synced table is not published).
- Every synced table gets a primary key `id text` (PowerSync requires a text `id`; domain ids are string UUIDs/ObjectIds, see Pitfall 10).
- A CI test: fresh database + migrations + bootstrap, then run `powersync validate` and a smoke sync.

**Warning signs:**
- "works on a fresh clone, not on my machine"; PowerSync connection errors after `git pull` on a reused volume; synced entity A works while newly added entity B never appears.

**Phase to address:** P3 Postgres adapters (migration tooling), P6 Self-host kit (bootstrap).

---

### Pitfall 8: PowerSync upload path bypasses the domain (mass assignment, wrong owner, non-idempotent replays)

**What goes wrong:**
The mobile connector's `uploadData()` sends `PUT`/`PATCH`/`DELETE` ops keyed by *table name* and *client-chosen* fields. A generic "apply this CRUD op to this table" endpoint becomes a mass-assignment hole: the client sets `owner`, `study_id`, `updated_by`, `archived`, or writes to a table the participant shouldn't write. Retries then re-apply ops, so a replayed `PUT` throws a 409 duplicate and a replayed `DELETE` throws 404; with the wrong status code the SDK either retries forever or the write is lost.

**Why it happens:**
It is easier to write one table-dispatch function than ~N entity handlers. The server is supposed to stay the authority (PROJECT.md requirement), but "authority" is only real if the endpoint reuses the same ports, validation, audit stamping, and authorization as REST.

**How to avoid:**
- Upload endpoint = thin adapter over existing use cases/ports, with an explicit allowlist of writable tables and writable columns per table; owner and audit fields are derived from the token and *ignored* if client-supplied.
- Apply an entire PowerSync transaction (batch of ops) atomically, which means adding a unit-of-work concept to the Postgres adapter; the current ports have none (see Pitfall 11).
- Idempotency: client-generated UUIDs for inserts (PowerSync best practice; domain `BaseEntity.id` already defaults to `uuid4`, but the REST create must accept a client-supplied id); treat `PUT` as upsert-for-owner; treat delete of an already-archived/absent row as success; dedupe by op id where semantics are non-idempotent.
- Status code contract, which determines queue behavior:
  - `2xx` for success *and* for permanent validation/business-rule rejections (report the rejection in the body or write it to a table that syncs back), then `complete()` the transaction.
  - `5xx` only for transient failures (DB down); the SDK retries.
  - Never return a permanent `4xx` for something that will never succeed, and never swallow a DB outage as "not found" (see Pitfall 11).
- The write endpoint must be synchronous with respect to the database commit; if it queues work for later, rows vanish locally and reappear.
- Preserve client capture time: `created_at` should be the client's event time, not server receipt time, for health data.

**Warning signs:**
- A single `/v1/sync/upload` handler with `getattr(repo, table)`; any code path where `owner` is read from the request body; the connector throwing on validation errors (blocks the upload queue permanently, a sync stall that looks like "offline mode").

**Phase to address:** P4 PowerSync backend (endpoint), P5 Mobile offline client (connector error handling).

---

### Pitfall 9: Concurrent token refresh by the API client and the PowerSync connector trips refresh-reuse detection

**What goes wrong:**
The mobile app uses rotating refresh tokens with server-side reuse detection (`session_store.py`). Now two components refresh: the Ktor `Auth` plugin and the PowerSync connector's `fetchCredentials()`. If both call `refresh` with the same refresh token concurrently, the second call looks like token reuse, the session family is revoked, and the user is logged out — while offline writes sit in the upload queue with no valid credentials.

**Why it happens:**
Rotating refresh tokens assume a single refresher. Offline-first apps wake from long offline spells and fire many requests at once; PowerSync will also reconnect and request credentials immediately.

**How to avoid:**
- A single shared `TokenProvider` in the KMP `core` module with a mutex/single-flight refresh used by both the Ktor client and `PowerSyncBackendConnector.fetchCredentials()`.
- Server-side: give the refresh endpoint a short grace window for the immediately-previous token (idempotent re-issue) so benign races don't revoke families; keep true reuse detection outside that window. Test with concurrent refresh calls.
- Refresh TTL (30 days) vs. offline duration: define behavior when the refresh token expires while offline writes are pending (keep the local DB and queue; require re-login as the *same* user; upload after re-auth).

**Warning signs:**
- Intermittent forced logouts after the app is foregrounded; refresh-reuse log lines with the same device id close together.

**Phase to address:** P5 Mobile offline client (provider), P2/P4 (server grace window).

---

### Pitfall 10: Port leakage and semantic drift when adding the Postgres adapter behind the flag

**What goes wrong:**
The Postgres adapters pass tests but behave differently from Couchbase/Mongo, and consumers (API, scheduler, PowerSync upload) get wrong results:
- **Ports carry datastore shapes.** Anything on a repository port that accepts or returns a Mongo operator dict (`execute_query`-style), N1QL fragments, `channels`, `_rev`, or `type` cannot be implemented cleanly in Postgres; adapters get forced to emulate Mongo/N1QL.
- **Ordering/pagination.** The current page token is base64url JSON `{"offset": n}`, opaque to clients. N1QL queries without `ORDER BY` return arbitrary order and tests pass by luck. In Postgres, `OFFSET` without a deterministic `ORDER BY` duplicates or skips rows, especially while a participant's device uploads concurrently.
- **Timestamps.** The domain uses `float` epoch seconds (`created_at: float = time.time`) plus integer tz offsets. Options (double precision vs `timestamptz`) have consequences: PowerSync syncs `timestamptz` to the client as ISO text and `double precision` as REAL; a float to datetime round-trip can change microseconds, so equality and last-write comparisons flake. `_local_tz_offset()` also uses the *server's* local timezone as a default.
- **IDs.** Domain ids are `str(uuid4())`, but Mongo-backed entities (users, participants, studies, devices) use ObjectId-style strings, and `get_by_id` catches `InvalidId`. A Postgres `uuid` column rejects non-UUID ids from the legacy flag or from imported fixtures. PowerSync requires a text `id` anyway.
- **Soft delete.** `archive`/`unarchive` semantics differ per adapter (Mongo `unarchive` swallows errors); Postgres needs one definition (`archived_at`/`archived` flag) honored by every list/count/filter.
- **Filter translation.** AIP `filter=` is translated to SQL; string-built `WHERE` is the Postgres analog of the f-string N1QL fragility already in CONCERNS.md.

**Why it happens:**
It is natural to "port" each Couchbase repository literally. With ~39 Couchbase and 8 Mongo repository modules there is also strong pressure to copy the Mongo base class, including its `except Exception: return None` and `print(traceback)` pattern.

**How to avoid:**
- Write a shared repository **contract test suite** parameterized over the in-memory fakes and the Postgres adapter (testcontainers, behind a marker so default `pytest` still needs no live infra). This is the single highest-value item for the migration: it defines behavior once.
- Audit the ports first; move anything datastore-shaped out of `application/` before writing Postgres code (Dependency Rule constraint in PROJECT.md).
- ADR for timestamps and ids before any schema is written. Recommended: `text` primary keys named `id`; epoch float vs `timestamptz` decided once, with a documented conversion function and a round-trip property test; if `timestamptz`, the PowerSync client schema declares `text` and the KMP side parses ISO-8601.
- Deterministic ordering: always `ORDER BY created_at, id` (or the resource's sort key); keep the opaque token but encode a keyset cursor internally when you are ready; reject old-shape tokens with the existing 400.
- Parameterize all SQL (SQLAlchemy Core/psycopg bind params); no f-string interpolation; extend the existing lint idea to Postgres and run it in CI.
- Never copy the Mongo exception pattern; catch only specific driver errors (`UniqueViolation`, `NoResultFound`) and let connection errors propagate to the global handlers.

**Warning signs:**
- A Postgres repository class with a method taking `dict` queries; adapter tests that mock the driver instead of using Postgres; list tests that assert order without specifying it.

**Phase to address:** P3 Postgres adapters (contract suite first); P1 for the error-swallowing fix in shared base code.

---

### Pitfall 11: Dual-backend flag decays; Postgres default silently breaks legacy deployments, and legacy can't use sync

**What goes wrong:**
The Couchbase/Mongo path is "retained behind a flag" but there is **no CI** in the repo, so once Postgres is the default the legacy adapters stop being exercised and break unnoticed; or Postgres-only features (refresh-session store, PowerSync upload endpoint, bootstrap command, migrations) are written against Postgres directly and hard-crash when the flag selects legacy. Mixed-store setups (users in Mongo, others in Couchbase today) get an unintended "half migrated" configuration if the flag is per-entity rather than global. Mobile with the legacy flag has no sync at all.

**Why it happens:**
Without CI, only the new path is ever run. The flag chooses a repository provider in the DI container, but auth persistence (`session_store.py`, Mongo-bound) and new endpoints bypass it.

**How to avoid:**
- Add CI in P1 before the migration (it also fixes the "no CI" gap): backend tests with fakes, the N1QL lint, frontend typecheck/lint/test.
- One global `DATASTORE_BACKEND=postgres|legacy` selector resolved once in the container; no per-entity mixing. Everything that persists (including refresh sessions, bootstrap/seed, upload endpoint) goes through ports.
- Declare a support matrix in docs: legacy backend = API/dashboard only, no PowerSync, frozen/best-effort; Postgres = full stack. State it in README so labs don't try legacy + mobile sync.
- Keep one smoke test per backend that imports and builds the container; real-database tests for legacy are optional but at least "container builds and wires every provider".

**Warning signs:**
- Postgres settings read at import time (breaks legacy startup); a feature that is "Postgres-only" with no guard and no doc note.

**Phase to address:** P1 Foundations (CI), P3 Postgres adapters (selector and matrix).

---

### Pitfall 12: Soft delete, purge, and consent withdrawal don't propagate to devices or to PowerSync storage

**What goes wrong:**
Three variants:
1. A participant archives an entry; the row is still in the stream; the app lists it as live (or the reverse: the stream filters out archived rows so `:undelete` appears as a brand-new insert and local drafts conflict).
2. A server `:purge` (hard delete) of a participant's data removes the Postgres row and the row leaves the device bucket, but PowerSync's bucket storage keeps operation history until compaction, and any data already synced remains on offline devices that haven't reconnected.
3. A client-side `DELETE` op from PowerSync gets mapped to *purge* instead of *archive*, which deviates from the REST `DELETE` semantic and destroys data.

**Why it happens:**
The domain's soft-delete is a persistence-port feature (`archive`/`unarchive`), not a column in the entity. Sync adds a second, device-side view of "deleted".

**How to avoid:**
- Pick the model once: sync an `archived` flag (so clients can render/restore) *or* filter archived rows out in the stream, and make every local query consistent with it. Recommended: sync the flag for participant-owned entries so `:undelete` is a simple update.
- Map client `DELETE` to `archive`; allow purge only through admin REST.
- For withdrawal/erasure, define a documented procedure: delete in Postgres, let PowerSync compact (verify compaction settings for self-hosted), revoke by key rotation if needed, and use a remote signal (a synced "wipe" flag) so the app clears its local DB on next connect. Do not claim erasure is instantaneous on offline devices.

**Warning signs:**
- No test of archive then undelete through sync; the sync config referencing `deleted`/`archived` inconsistently across streams.

**Phase to address:** P4 PowerSync backend (semantics), P5 for the client wipe; P7 for the documented procedure.

---

### Pitfall 13: Initial sync and client storage blow up on wearable-scale data

**What goes wrong:**
"Sync full participant-scoped data" with ~50 entities includes Fitbit and ActiGraph records that can be minute- or sub-minute-level. First launch downloads months of raw data over mobile networks, takes many minutes, fills storage, and hits PowerSync limits (default 1,000 buckets per connection; 1,000 parameter-query results per user; `PSYNC_S2305` when exceeded). On the server, a wearable backfill writes thousands of rows in a burst, creating replication spikes (the Service replicates roughly 5k ops/s; memory spikes and lag if far beyond).

**Why it happens:**
Legacy parity ("all data offline") is taken literally. Bucket count explodes when streams are keyed on joined tables rather than the user id, or with `OR`.

**How to avoid:**
- Tier the data: small, user-authored entities (weights, goals, surveys, messages) sync in full; high-volume sensor data syncs a bounded window (e.g. last N days) or summaries, using subscription-parameter-narrowed streams where the parameter only *narrows* an auth-scoped query (never widens it).
- Key buckets on a column of the synced table (`owner`), group same-filter queries into one stream; check bucket and parameter-result counts in logs.
- Use prioritized sync so critical tables arrive first.
- Load test with a realistic synthetic participant (e.g. 90 days of ActiGraph and Fitbit) before declaring P4 done; measure first-sync time and device DB size.
- Throttle/batch server ingestion writes.

**Warning signs:**
- Initial sync > a couple of minutes on the demo seed; `PSYNC_S2305` in logs; PowerSync memory climbing during a seed load.

**Phase to address:** P4 PowerSync backend (stream design), P5 for client behavior; re-check scope decision "sync full participant-scoped data in v1".

---

### Pitfall 14: Schema evolution breaks field devices and the sync config

**What goes wrong:**
A migration renames or drops a column on a synced table, or adds a NOT NULL column. Old app versions in the field (no forced updates for dev builds and research apps) upload ops with the old shape and get rejected, or the sync config referencing the old column fails to deploy. Each sync-config redeploy re-snapshots tables, which is expensive and uses a second replication slot.

**Why it happens:**
Normal backend migration discipline ("rename and move on") ignores that clients have a separately versioned local schema (PowerSync client schema is code in the app, applied as SQLite views over a generic store, so it tolerates additive changes but not semantic changes).

**How to avoid:**
- Additive-only changes to synced tables within a release line (expand, then later contract after all supported app versions are retired).
- Upload endpoint tolerant of unknown/missing fields for older clients; version the connector, or send an app-version header and have the server reject too-old clients with a clear "update required" signal.
- Keep the client `Schema` and the server sync config in one reviewed change set; add a CI check that every column referenced in the sync config exists in the migrated database and every synced table is in the client schema.
- Plan sync-config deploys as operations (WAL budget, slot headroom, snapshot time).

**Warning signs:**
- Alembic autogenerate diff touching synced tables with `drop_column` or `alter_column` renames.

**Phase to address:** P3 (policy), P4 (CI check), P5 (client schema).

---

### Pitfall 15: Self-host kit ships with real, working default secrets and exposed ports

**What goes wrong:**
`docker compose up` on a VM exposes Postgres (5432), Redis (6379), the PowerSync port, and the mail catcher UI to the internet. Docker publishes ports by editing iptables, bypassing `ufw` rules, so a lab thinks they're firewalled. Redis has no password (it holds OTP records and rate limits; the Celery broker). Defaults like `POSTGRES_PASSWORD=postgres` or an `.env.example` with a placeholder JWT secret that happens to satisfy the 32-character boot guard get deployed as-is. The Couchbase `Administrator/password` defaults in settings classes already exemplify the pattern. The dev mail catcher captures OTP emails: if enabled in production, anyone with UI access can read login codes.

**Why it happens:**
"One command" convenience pushes dev defaults into the only compose file; the boot guard checks length, not randomness or known-example values.

**How to avoid:**
- Two explicit modes: `docker-compose.yml` (dev, secure-ish localhost binding) and a production override/profile; dev-only services (mail catcher, demo seed) live in a `dev` profile that the production guide never enables.
- Bind every non-public port to `127.0.0.1:` (`"127.0.0.1:5432:5432"`) or do not publish it at all; only the reverse proxy exposes 80/443 (plus PowerSync via the proxy).
- Boot guard rejects known example values (a denylist including whatever `.env.example` ships) and weak/short secrets for JWT secret/pepper and DB passwords; require all DB credentials with no defaults (also fixes CONCERNS.md items for Couchbase/Mongo).
- Ship `scripts/gen-secrets` (or `make secrets`) that writes a fresh `.env` with random values; `.env.example` contains obvious placeholders like `CHANGE_ME_*` that fail the guard.
- Redis `requirepass` and, for production, AOF persistence (current `redis:7-alpine` is non-persistent: restart clears OTP and queues).
- Trust `X-Forwarded-For` only from the proxy (`--forwarded-allow-ips`), documented with the proxy chain (CONCERNS.md).

**Warning signs:**
- `ports:` entries without a `127.0.0.1` prefix; the same password string in README and compose; the example `.env` working without edits.

**Phase to address:** P6 Self-host kit; P7 for the hardening checklist.

---

### Pitfall 16: Bootstrap/seed is insecure or non-repeatable

**What goes wrong:**
First-admin creation is done with a hard-coded default admin email, a setup HTTP endpoint that stays reachable (first caller wins the admin), or a seed that creates demo participants with realistic-looking data in production. Login is email OTP, so with no SMTP configured the admin cannot log in at all, and the failure looks like an app bug. Bootstrap run twice creates duplicates or errors.

**How to avoid:**
- CLI-only, idempotent bootstrap (`python -m openwellness_api.bootstrap --admin-email you@lab.edu`) that requires an email argument; no default; no HTTP setup endpoint.
- Demo data behind an explicit `--demo` flag that refuses to run when `ENVIRONMENT=production` (or when SMTP is a real host), and marks demo rows.
- Preflight check in the CLI/API startup: warn loudly when SMTP is unset in non-dev mode; in dev, route OTP to the mail catcher.
- Test the bootstrap on a fresh database in CI, followed by an OTP login via the catcher API.

**Warning signs:**
- README quick start has a manual SQL/Mongo shell step; a fresh clone requires "ask the original team" knowledge (the exact failure PROJECT.md's Core Value targets).

**Phase to address:** P6 Self-host kit.

---

### Pitfall 17: Documentation drifts from reality and is never executed

**What goes wrong:**
The README gap audit already found broken quick-start steps (`.env` never loaded; missing `API_AUTH_*`; wrong `REDIS_URL` default; `uv sync` vs `--extra dev`; wrong refresh-session store location). After this milestone the docs describe PowerSync, Postgres, TLS, and mobile URLs — four times more surface to drift — and nobody notices because there is no CI.

**How to avoid:**
- Execute the docs: a CI job (or scripted check) that does a fresh clone, runs the documented quick start in containers, and curls health plus OTP login via the mail catcher.
- Generate the configuration reference table from the Pydantic settings classes (script) and fail CI if the checked-in doc differs; same for `.env.example` (every required var present, no extra undocumented vars).
- Settings must load `.env` identically under compose and direct runs (`env_file` in `SettingsConfigDict`), with one shared settings module in `core` (also resolves the duplicated settings classes in api/scheduler).
- Single source of truth for URLs/ports consumed by compose, `service.yaml`, API, and mobile (PowerSync config supports env substitution; verify the `!env` tag for the pinned PowerSync version).

**Warning signs:**
- A variable in `docker-compose.yml` not present in `.env.example`; docs naming a file path that no longer exists.

**Phase to address:** P1 (settings/.env), P6 (generation scripts), P7 (docs verification).

---

### Pitfall 18: Reverse proxy and networking break the sync stream and the mobile app

**What goes wrong:**
Locally everything works; behind nginx/Caddy/Traefik the PowerSync stream stalls or reconnects every 60 seconds because of proxy buffering and idle timeouts (sync uses long-lived HTTP streaming/WebSocket). The app also needs *two* reachable HTTPS endpoints (API and PowerSync). On mobile: Android emulator needs `10.0.2.2` for the host, iOS simulator `localhost`, physical devices need the LAN IP; Android blocks cleartext HTTP by default and iOS App Transport Security blocks non-HTTPS, so "point at my dev server" fails without TLS or explicit exceptions. PowerSync's `jwks_uri` pointed at `localhost` inside its own container resolves to itself.

**How to avoid:**
- Ship a tested reverse-proxy config (Caddy recommended for automatic TLS) that disables response buffering and sets long read timeouts on the PowerSync route; verify with a soak test.
- One documented `API_BASE_URL` and one `POWERSYNC_URL` in mobile build config, per platform, with explicit dev-mode cleartext exceptions limited to debug builds.
- All inter-container URLs use compose service names; test with a non-localhost hostname.

**Warning signs:**
- Sync "connected" then disconnects at consistent intervals; iOS app can't reach `localhost` URL only on a real device.

**Phase to address:** P7 Docs and prod guide (proxy), P8 Mobile server config.

---

### Pitfall 19: Health-data compliance posture claimed or ignored (HIPAA/IRB expectations)

**What goes wrong:**
Two opposite failures. (a) Docs or marketing say "HIPAA compliant" for software, which is not a thing a codebase can be; compliance depends on the deploying institution's configuration, agreements, and policies. (b) The kit ignores baseline expectations an IRB or institutional security office will ask about: encryption in transit between *all* components (including Postgres and Redis connections), encryption at rest, audit logging of who accessed/changed participant data, minimum necessary access, retention and deletion, and no participant data in logs. This codebase currently prints tracebacks (with document ids/query contents) to stdout, has no audit log (`updated_by` was spoofable), and sends OTP emails with participant addresses through whatever SMTP the lab picks (a third-party processor of identifiers).

**How to avoid:**
- Write a "Security and compliance responsibilities" page: what the platform provides, what the lab must provide (disk encryption, TLS certs, backups, access control, SMTP provider agreement, IRB protocol alignment), with an explicit non-claim of certification.
- Provide a hardening checklist: encrypted volumes, TLS to Postgres (`sslmode=require`) even on one VM if the DB is not on a loopback/private network, firewall rules, SMTP over TLS, log retention, OS patching.
- Add a minimal append-only audit table for data-changing and admin actions (CONCERNS.md gap), written server-side from the authenticated principal; at least log reads of participant data by coaches/admins.
- Replace `print` with structured logging that redacts identifiers; never log request bodies of health data or OTP codes.
- Verify what telemetry the self-hosted PowerSync service and containers emit by default and document how to disable it (verify against the pinned version's usage-reporting settings).
- Define data deletion/withdrawal and backup retention in the lab-facing docs (backup copies are also participant data).

**Warning signs:**
- Plaintext Postgres/Redis traffic crossing a network boundary; logs containing emails or entity ids; docs that never mention retention.

**Phase to address:** P2 (audit stamping/log redaction), P7 (compliance page and checklist).

---

### Pitfall 20: Backups that don't restore, and secrets that aren't backed up

**What goes wrong:**
Backups are `pg_dump` on a cron that nobody has restored; PowerSync's bucket storage (MongoDB or Postgres-based) is assumed to need backing up (it's derived data and can be rebuilt from the source DB) while the actual loss risks are ignored: the `.env` (JWT/pepper secrets; losing or rotating them invalidates all sessions and possibly pepper-derived markers — verify which stored values depend on the pepper), Redis state, and the Postgres replication state. After a restore to a new database, existing replication slots don't exist; PowerSync re-creates the slot and re-replicates, so devices resync, but a restore to an *older* point means devices can hold data that the server no longer has, then re-upload stale ops.

**How to avoid:**
- Documented, scripted backup (`pg_dump`/`pg_basebackup`, optionally WAL archiving) and a **tested** restore procedure in CI or release checklist: restore to a clean stack, run PowerSync, connect a device.
- State what is *not* backed up and why (bucket storage is reconstructible), and back up secrets separately and encrypted.
- Restore runbook includes: recreate publication/role, drop stale slots, restart PowerSync, expect full re-snapshot and temporary resync on clients.
- Encrypt backups, keep them off the same disk, apply retention consistent with the lab's IRB protocol.

**Warning signs:**
- Backup section in the guide without a restore section; no mention of secrets in the backup list.

**Phase to address:** P7 Docs and prod guide.

---

## Moderate Pitfalls

### Pitfall 21: Local device database holds health data in the clear and leaks through OS backups

**What goes wrong:** The PowerSync SQLite file lives in the app sandbox. Android Auto Backup (`allowBackup` defaults to true) can copy it to the user's cloud account; iOS app-support directories can be included in iCloud/iTunes backups. A lost, unlocked, or shared device exposes everything synced.
**Prevention:** Set `android:allowBackup="false"` or `dataExtractionRules`/`fullBackupContent` to exclude the DB; mark the DB directory excluded from iCloud backup on iOS; require device passcode (document it); evaluate encrypted database support in the KMP SDK (verify availability for the pinned version) and decide explicitly. Keep screenshots/notifications free of PHI.
**Phase:** P5.

### Pitfall 22: Logout / account switch wipes unsynced writes or leaves another user's data

**What goes wrong:** Calling `disconnectAndClear()` on logout discards pending uploads (silent data loss for a participant who logged out while offline). Conversely, not clearing on logout leaves participant A's data on a shared device when participant B logs in.
**Prevention:** On logout, check the upload queue; if non-empty and offline, warn and block clearing (or keep the queue under the same user and clear after upload). On login with a different user id, clear the DB. Test both paths.
**Phase:** P5.

### Pitfall 23: Soft conflicts hidden by last-write-wins with server-time stamping

**What goes wrong:** PowerSync's default is per-field last-write-wins on the server, in upload order. If the API restamps `updated_at` with server time, a delayed offline edit overwrites a newer edit made on another device or by a coach. Deletes win over later updates. There is no "increment" op for counter-style data. Rejected writes are silently dropped from the participant's perspective.
**Prevention:** Decide per entity: client-authored entries (weights, journals) are append-mostly; server-authored fields (coach messages, study settings) are read-only on the client (not in the upload allowlist). Keep client event timestamps; surface rejected writes via a synced status table or an error list in the app.
**Phase:** P4/P5.

### Pitfall 24: Scheduler additions run twice, or not at all

**What goes wrong:** Adding a beat service but scaling `scheduler` workers with `--scale` (or running beat inside every worker with `-B`) schedules each job N times. Conversely, no beat leaves ingestion and cleanup (e.g., refresh-session cleanup, WAL-health checks) unrun. Data "ingested on the server syncs down" can't be demonstrated without any ingestion job in-repo.
**Prevention:** Exactly one `beat` service, separate from workers; persist its schedule file or use a DB scheduler; make tasks idempotent; give the demo a seed command that writes wearable rows through the domain ports (not raw SQL) to exercise sync-down.
**Phase:** P6.

### Pitfall 25: Connection pool and process-count arithmetic

**What goes wrong:** `--workers 2` uvicorn x pool size + Celery worker concurrency x pool size + PowerSync + migrations exceed `max_connections`. Sync `def` handlers run in a threadpool, each blocking on a connection. PgBouncer in transaction mode in front of Postgres breaks the logical replication connection PowerSync needs.
**Prevention:** Compute and document the connection budget; size pools explicitly; PowerSync connects straight to Postgres; keep pooler optional and never in front of the replication role.
**Phase:** P3/P7.

### Pitfall 26: Startup ordering and healthchecks hide failures

**What goes wrong:** Compose `depends_on` without `condition: service_healthy` starts the API before Postgres/migrations; PowerSync starts before the publication exists; the existing lifespan in `main.py` can leak the datastore connection if `container.wire` fails before the `try`; health endpoints (PowerSync's) return status only, not root cause.
**Prevention:** Health checks on Postgres, Redis, API, PowerSync; `migrate` as a one-shot dependency; fix lifespan cleanup ordering (CONCERNS.md); use PowerSync Diagnostics API for root cause; scheduler health check.
**Phase:** P1/P6.

### Pitfall 27: PowerSync licensing and version pinning

**What goes wrong:** Self-hosted "Open Edition" of the PowerSync Service has its own license terms and a fast-moving config schema (Sync Rules are now legacy in favor of Sync Streams; storage versions; `Sync Config` naming). Docs/config examples found online mix generations. Using `latest` image tags makes the self-host kit non-reproducible.
**Prevention:** Pin image tags (PowerSync service, Postgres, Redis, mail catcher) and the KMP SDK version together; choose Sync Streams (current) unless a blocker exists; check the service license against the project's NOTICE/license before redistributing a kit (verify); record the chosen config format in an ADR.
**Phase:** P4.

### Pitfall 28: Migration tooling race and drift

**What goes wrong:** Migrations are executed at app startup by every worker; two processes race on the same DDL; autogenerate hides drift; the "fresh database reproducible" requirement is unverified.
**Prevention:** One-shot `migrate` service with advisory lock; CI job: apply all migrations to empty Postgres, then check `alembic check` (model/schema drift) and run the contract suite on it.
**Phase:** P3.

---

## Minor Pitfalls

### Pitfall 29: Dashboard hosting details
`VITE_API_BASE_URL` is baked at build time; the production guide must say rebuild-per-environment, and CORS origin must exactly match scheme+host+port. Refresh token in `localStorage` (CONCERNS.md) becomes a more serious exposure once the dashboard is internet-facing; add CSP and plan the cookie move (not blocking).
**Phase:** P7.

### Pitfall 30: Rate limiting trusts `X-Forwarded-For`
Once a proxy is introduced, either every request appears from the proxy IP (limit hits everyone) or the header is spoofable. Configure trusted proxies; test through the real proxy.
**Phase:** P7.

### Pitfall 31: Dead configuration suggests a migration path that doesn't exist
`legacy_verified_id_salt` is read nowhere. Remove it in P1 so lab operators don't set it and expect compatibility.
**Phase:** P1.

### Pitfall 32: Test infrastructure assumptions
`mongomock` and fakes do not enforce index conflicts, TTLs, or SQL semantics; Postgres tests need a container; developers without Docker can't run them. Keep the default `pytest` run infra-free and gate Postgres tests with a marker plus a CI job that always runs them.
**Phase:** P3.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `enforce_principal` as a toggle | Staged rollout, no client breakage | Open API in any lab that omits the env var | Never in the shipped product; acceptable only on a short-lived branch for finding call sites |
| Share HS256 secret between API and PowerSync | Sync works in an afternoon | Key sprawl, PowerSync says dev-only, no rotation story | Local dev compose profile only |
| Generic table-dispatch upload endpoint | One handler for all entities | Mass assignment, bypasses domain validation | Never; allowlist per table and column |
| Store every entity as one JSONB `doc` column (Couchbase-style) | Fastest port of ~40 repositories | Can't index or filter well, sync rules need `json_extract`, painful constraints | Only for sparse nested payloads inside a typed row |
| `FOR ALL TABLES` publication | One-liner from the docs | Auth/session/PII tables replicate; new tables auto-publish | Never in a shared kit |
| Run migrations in app startup | No extra compose service | Races across workers, can't separate privileges | Never with multiple workers |
| Sync every entity in full | Legacy parity | Huge initial sync, bucket limits, device storage | Small user-authored entities only |
| `latest` image tags | Always current | Non-reproducible kit, config schema breaks | Never in the shipped kit |
| Skip the contract test suite and test adapters via mocks | Faster adapter delivery | Behavioral drift between backends, ghost bugs | Never |
| Defer CI to "after the migration" | Focus on features | Legacy path rots unobserved; docs drift | Never; CI is the first deliverable |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PowerSync and Postgres | Default `wal_level`, no role, publication name other than `powersync` | `wal_level=logical`, role `REPLICATION BYPASSRLS LOGIN` with `SELECT`, publication named `powersync` listing only synced tables |
| PowerSync and Postgres | No `max_slot_wal_keep_size`; headroom for 2 slots per deploy missing | Set the cap and `max_replication_slots`; monitor `pg_replication_slots` |
| PowerSync JWT | `kid` absent, `aud` mismatch, `exp - iat` > 24h, localhost JWKS URL | Asymmetric key + `kid`, matching `client_auth.audience`, 15-60 minute TTL, compose-hostname JWKS |
| PowerSync client | `uploadData` throws on validation errors, forgets `complete()` | `2xx` for permanent rejections plus `complete()`, `5xx` for transient |
| PowerSync client | Using Postgres types naively | `timestamptz` arrives as ISO text, `uuid`/`json`/`numeric`/arrays as text, boolean as 0/1, `bytea` can't sync directly; model in the client schema accordingly |
| PowerSync storage | Assuming bucket storage needs backing up | It is derived; the source Postgres is the system of record. Self-hosted storage is MongoDB (replica set required for change streams) or Postgres, so the kit adds another datastore to operate (verify the chosen storage option) |
| Ktor and PowerSync | Two independent token refreshers | One shared single-flight TokenProvider |
| Reverse proxy | Default buffering/timeouts | Disable buffering and extend timeouts for the sync route |
| SMTP | Real SMTP in dev, mail catcher in prod | Profile-driven; catcher only in dev; real SMTP over TLS in prod |
| Celery and Redis | Non-persistent Redis as the only record of OTP and broker | AOF for production; accept OTP loss on restart as a UX cost, document it |
| Postgres and Docker | `ports: "5432:5432"` | Bind to 127.0.0.1 or no publish |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| OFFSET pagination with large tables and no deterministic order | Slow list pages, duplicates/skips | `ORDER BY` stable key; keyset cursor internally; composite indexes on `(owner, created_at)` | Fitbit/ActiGraph tables with >100k rows per participant |
| `list_all`-style unbounded reads ported to Postgres | Memory spikes in API | Remove or paginate; never `fetchall` on user-scale tables | Any production-size study |
| Missing indexes on `owner`, `study_id`, time columns | Slow filters, slow stream queries and initial snapshots | Index the same columns the sync streams filter on | Thousands of participants x months of data |
| Per-op uploads | Slow catch-up after long offline period | Batch endpoint applying a PowerSync transaction per request | Participants offline for days with many entries |
| Wearable ingestion burst through ORM row-by-row | Replication lag, PowerSync memory spikes | Bulk insert (COPY/executemany), throttle | Backfill of months of minute-level data |
| Blocking drivers in threadpool with small pools | 502s/timeouts under load | Explicit pool/threadpool sizing, measure first | Tens of concurrent active devices uploading |
| Streams with `OR` or joined keys | Bucket count growth, `PSYNC_S2305` | Key on owner column, one stream per filter shape | Users with many studies/groups |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Router not deny-by-default | Open health data (current state) | Router-level dependency + route-enumeration test |
| IDOR on `{user}` paths and filter overrides | Cross-participant disclosure | Token-subject binding, scope before filter, hostile-filter test |
| Coach role without study membership | Cross-study disclosure | Authorize by assignment |
| Trusting `X-Principal-Id` | Forged audit trail | Remove; stamp only from verified token |
| Client-controlled sync parameters used for scoping | Cross-participant data on devices | Auth-parameter-only scoping + isolation test |
| Replicating auth/session/OTP tables | Secrets in extra datastore | Explicit publication list |
| Refresh token in `localStorage` | XSS session theft | CSP now, HttpOnly cookie later |
| Known default secrets or unauthenticated Postgres/Redis exposed | Full compromise | Guard denylist, 127.0.0.1 binding, generated secrets |
| Mail catcher or Diagnostics API exposed in prod | Read OTPs, leak internals | Dev profile only; PowerSync API token set; do not expose admin/diagnostics port publicly |
| Health data in logs / tracebacks | Compliance incident | Structured logging, redaction, no `print` |
| Unencrypted device DB and OS backup inclusion | Disclosure on lost device | Backup exclusion, passcode requirement, evaluate DB encryption |
| Mongo operator injection via `execute_query(dict)` pattern copied to Postgres | Query injection | Typed query builders, bind parameters |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent upload failure (queue blocked) | Participant thinks data is saved, researchers miss it | Visible sync status, pending-count indicator, surfaced rejected writes |
| Forced logout on token race | Lost trust, stuck offline writes | Shared refresh, grace window |
| First-launch sync with no progress | App seems frozen on cellular | Prioritized sync, progress UI, Wi-Fi hint, bounded history |
| OTP email not arriving (no SMTP/ catcher confusion) | Cannot log in at all | Preflight warnings, documented dev catcher URL |
| Logout while offline discards entries | Data loss | Block or warn on pending uploads |
| "Update required" not signaled after schema change | Mysterious failures | App-version header + explicit 426-style handling mapped to a clear message |

## "Looks Done But Isn't" Checklist

- [ ] **Auth enforcement:** often missing new/unlisted routes and non-owner resources — verify via an automated test that iterates every registered route and expects 401 anonymous, 403 wrong-user.
- [ ] **Owner binding:** often missing `filter=` and list-endpoint scoping — verify a hostile filter returns no foreign rows.
- [ ] **Role model:** often missing coach-study membership and admin list gating — verify with a coach from study A against study B.
- [ ] **Postgres adapters:** often missing archive/undelete, deterministic order, and error mapping — verify the shared contract suite passes on fakes and Postgres.
- [ ] **Fresh DB reproducibility:** often missing grants/publication — verify empty database -> migrate -> bootstrap -> PowerSync connects in CI.
- [ ] **Refresh sessions on Postgres:** often missing expiry cleanup (no Mongo TTL) — verify a scheduled cleanup exists and reuse detection still works.
- [ ] **Sync isolation:** often missing a negative test — verify participant B's token never receives A's rows, on every stream.
- [ ] **Upload path:** often missing idempotent replay and owner override — verify duplicate PUT/DELETE and a forged `owner` field.
- [ ] **Offline behavior:** often only tested online — verify airplane mode: create, edit, kill app, reconnect, data reaches server and other device.
- [ ] **Server-ingested data syncs down:** often demonstrated with raw SQL — verify via the ingest path/ports and see it on a device.
- [ ] **WAL safety:** often missing `max_slot_wal_keep_size` — verify stopping PowerSync for an hour under write load does not grow WAL without bound.
- [ ] **Self-host kit:** often passes only on the author's machine/volume — verify a fresh clone on a clean VM and after `docker compose down` + `up` on an old volume.
- [ ] **Secrets:** often example values work — verify the API refuses to boot with `.env.example` as-is.
- [ ] **Ports:** often published on 0.0.0.0 — verify `ss -tlnp` on the VM shows only 80/443 public.
- [ ] **Backups:** often no restore test — verify the documented restore on a clean machine.
- [ ] **Docs:** often drifted — verify the CI job that executes the quick start passes, and the config reference matches the settings classes.
- [ ] **Mobile:** often hard-coded localhost — verify a device build against a remote HTTPS server for both the API and PowerSync URLs on Android and iOS.
- [ ] **Beat:** often a worker with no scheduler — verify a periodic task actually fires once per interval.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Cross-participant leak found in sync config | HIGH | Disable the stream / rotate JWT signing key to invalidate tokens, fix filter, add isolation test, redeploy sync config, assess disclosure obligations with IRB/institution, clear affected device DBs via wipe flag |
| WAL disk full | MEDIUM | Add disk or emergency space, drop the orphaned/invalidated slot (`pg_drop_replication_slot`), CHECKPOINT, raise `max_slot_wal_keep_size`, restart PowerSync (full re-snapshot) |
| Slot invalidated during snapshot (`PSYNC_S1146`) | LOW | Increase cap, drop slot, restart service |
| Open API discovered in a deployment | HIGH | Take offline, deploy enforcement, rotate JWT secret (invalidates sessions), review access logs (limited, no audit table yet), notify per institution policy |
| Upload queue permanently blocked on devices | MEDIUM | Ship connector fix that completes the poisoned transaction (log the discarded op), server returns 2xx with a rejection record, add queue-depth telemetry |
| Forced-logout storm from refresh race | MEDIUM | Server grace window hotfix; client single-flight in next build |
| Wrong timestamp/id type chosen after data exists | HIGH | New migration with column rewrite, adapter conversion, client schema bump; avoided by the P3 ADR |
| Default secrets deployed | MEDIUM | Rotate all secrets, force re-login, change DB credentials, check access logs |
| Backups unrestorable | HIGH | Treat as data loss risk; build restore drill immediately; keep the old volume until a restore is proven |
| Legacy flag path broken | MEDIUM | Restore from CI-failing commit bisect; reduce support claim to "frozen" in docs |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 Open routes / flag | P2 | Route-enumeration 401 test in CI |
| 2 Owner binding, coach scope, filter | P2 | Two-user/two-study tests, hostile filter test |
| 3 Client breakage, upload path auth | P2, P4 | Dashboard and mobile smoke against enforced API |
| 4 HS256 sharing, `kid`, `aud` | P4 (ADR early) | PowerSync connects with asymmetric JWKS in compose |
| 5 Sync scoping leakage | P4 | Automated sync isolation test with 2 tokens |
| 6 WAL growth | P6, P7 | Stop-PowerSync soak test; monitoring query documented |
| 7 Bootstrap vs migrations | P3, P6 | Fresh and reused volume both start |
| 8 Upload mass assignment/idempotency | P4, P5 | Forged owner field rejected; duplicate op safe |
| 9 Token refresh race | P5 (+ P2/P4 grace) | Concurrent-refresh test; no forced logout |
| 10 Port leakage, semantics, ids, timestamps | P3 (P1 for error handling) | Shared contract suite, ADR, round-trip test |
| 11 Dual backend decay | P1, P3 | CI runs both container builds; support matrix in README |
| 12 Soft delete / purge / withdrawal | P4, P5, P7 | Archive->undelete through sync; wipe procedure test |
| 13 Initial sync scale | P4, P5 | 90-day synthetic participant benchmark |
| 14 Schema evolution | P3, P4, P5 | CI check sync config columns vs migrated schema |
| 15 Default secrets and exposed ports | P6, P7 | Boot guard test with example values; `ss -tlnp` check |
| 16 Bootstrap/seed | P6 | Fresh-DB CLI test + OTP login via catcher |
| 17 Docs drift | P1, P6, P7 | Executed quick-start CI; generated config reference |
| 18 Proxy/networking/mobile URLs | P7, P8 | Soak through proxy; device build on remote HTTPS |
| 19 Compliance posture | P2, P7 | Audit table present; compliance page; no PHI in logs |
| 20 Backups/restore | P7 | Restore drill documented and run |
| 21 Device DB exposure | P5 | Manifest/backup rules inspected |
| 22 Logout data loss | P5 | Offline logout test |
| 23 LWW surprises | P4, P5 | Per-entity write-policy table |
| 24 Beat | P6 | Periodic task fires once |
| 25 Connection budget | P3, P7 | Documented budget; load test |
| 26 Healthchecks/startup | P1, P6 | `compose up` ordering test |
| 27 Licensing/pinning | P4 | Pinned tags; ADR |
| 28 Migration races | P3 | One-shot migrate service in CI |

## Sources

- PowerSync, Postgres source DB setup (wal_level, role, `powersync` publication, slots): https://docs.powersync.com/configuration/source-db/setup (HIGH, official docs, fetched 2026-10-29)
- PowerSync, Postgres maintenance (slot cleanup, `max_slot_wal_keep_size`, invalidation, slot per deploy): https://docs.powersync.com/configuration/source-db/postgres-maintenance (HIGH)
- PowerSync, production readiness (WAL budget, monitoring, Diagnostics API, `PSYNC_S1146`): https://docs.powersync.com/maintenance-ops/production-readiness-guide (HIGH)
- PowerSync, custom authentication (claims, `kid`, `aud`, HS256 dev-only, JWKS rotation, no revocation): https://docs.powersync.com/installation/authentication-setup/custom (HIGH)
- PowerSync, Sync Streams parameters (auth vs subscription vs connection trust): https://docs.powersync.com/sync/streams/parameters (HIGH)
- PowerSync, Sync Streams overview and bucket count limits: https://docs.powersync.com/sync/streams/overview and https://docs.powersync.com/sync/streams/bucket-count (HIGH)
- PowerSync, writing client changes (complete(), 2xx vs 5xx, blocked queue): https://docs.powersync.com/handling-writes/writing-client-changes (HIGH)
- PowerSync, handling update conflicts (server-authoritative, LWW, deletes win, idempotency): https://docs.powersync.com/handling-writes/handling-update-conflicts (HIGH)
- PowerSync, Kotlin Multiplatform SDK reference (targets, schema as views, text id, web experimental, iOS notes): https://docs.powersync.com/client-sdks/reference/kotlin (HIGH)
- PowerSync, types mapping (timestamptz, numeric, boolean, json, bytea): https://docs.powersync.com/sync/types (HIGH)
- PowerSync, service architecture (bucket storage MongoDB or Postgres, snapshot/reprocessing): https://docs.powersync.com/architecture/powersync-service (HIGH)
- PowerSync, self-host demo and local development (MongoDB replica set for bucket storage, `client_auth` jwks/audience): https://github.com/powersync-ja/self-host-demo and https://docs.powersync.com/configuration/powersync-service/self-hosted-instances (MEDIUM, from search snippets, not read in full)
- Project files: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/ARCHITECTURE.md`; code reads of `backend/api/src/openwellness_api/common/pagination.py`, `auth/token_service.py`, `config.py`, `backend/core/src/openwellness_core/domain/models/base_entity.py`, `base_owner_entity.py` (HIGH)
- Docker published ports bypassing host firewall (ufw/iptables), HIPAA/IRB expectations for research data, Android Auto Backup and iOS backup inclusion of app data, reverse-proxy buffering and sync streams: based on established practice, not fetched in this session (MEDIUM; verify during the relevant phase)

---
*Pitfalls research for: Postgres migration + PowerSync offline-first + auth enforcement + self-host kit (OpenWellness)*
*Researched: 2026-10-29*
