# Architecture Patterns

**Domain:** Integrating Postgres + PowerSync into an existing Clean Architecture (ports and adapters) Python backend and Kotlin Multiplatform mobile app
**Researched:** 2026-10-29
**Overall confidence:** MEDIUM-HIGH (codebase facts HIGH, verified by reading source; PowerSync behavior HIGH where quoted from official docs, MEDIUM where inferred; items marked VERIFY need a spike before commitment)

## Recommended Architecture

Postgres is a new adapter family behind the existing ports. PowerSync is a read-only replication consumer of Postgres plus a client SDK. It is never a writer. The API (and scheduler) remain the single writer to Postgres, so server authority, validation and audit stamping are unchanged.

```
 Mobile (KMP)                                                    Dashboard (React)
 ┌───────────────────────────────────┐                          ┌──────────────────┐
 │ feature:*:presentation  (Compose) │                          │ online REST only │
 │ feature:*:domain  (use cases,     │                          └────────┬─────────┘
 │        repository interfaces)     │                                   │
 │ feature:*:data  (Local*Repository │                                   │
 │        over PowerSync SQL)        │                                   │
 │ core:sync  (PowerSyncDatabase,    │                                   │
 │   Schema, ApiBackendConnector)    │                                   │
 │ core:data  (Ktor HttpClient,      │                                   │
 │   rotating refresh, token store)  │                                   │
 └───────┬───────────────▲───────────┘                                   │
  writes │ uploadData    │ sync stream (read-only)                        │
  (AIP   │ (queued ops)  │ JWT = API access token                         │
  REST)  ▼               │                                                ▼
 ┌─────────────────┐  ┌──┴───────────────────┐        ┌───────────────────────────────┐
 │ API (FastAPI)   │  │ PowerSync Service    │        │ API /v1 (same process)        │
 │ /v1 router:     │  │ verifies JWT (kid +  │        │                               │
 │  require_principal │ JWKS/HS256 key)      │        └───────────────────────────────┘
 │  + owner binding│  │ streams scoped by    │
 │  + role gates   │  │ auth.user_id()       │
 └───────┬─────────┘  └──┬──────────▲────────┘
         │ ports          │ logical  │ bucket storage
         ▼                │ replic.  │ (Postgres DB #2, or Mongo)
 ┌──────────────────────┐ │          │
 │ core: Repository     │ │          │
 │ ports (unchanged)    │ │          │
 ├──────────────────────┤ │          │
 │ adapters/postgres/*  │─┼──write──▶│
 │ adapters/couchbase/* │ │ (legacy flag only)
 │ adapters/mongo/*     │ │
 └──────────┬───────────┘ │
            ▼             ▼
      ┌──────────────────────────────┐        Scheduler (Celery) ──ports──▶ same Postgres
      │ Postgres (wal_level=logical) │        (wearable ingestion writes here; PowerSync
      │ publication "powersync" =    │         picks the rows up from the WAL, no extra code)
      │ synced tables ONLY           │
      └──────────────────────────────┘
```

Core principle: **one write path, one read-replication path.** Writes go device -> local SQLite -> upload queue -> `/v1` REST -> port -> Postgres. Reads go Postgres WAL -> PowerSync -> device SQLite. The only thing that touches both is the row `id` and `owner` columns.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `core/domain` + `core/application` (ports) | Entities and repository contracts; **no changes of kind**, only the small purification edits listed under "Required changes to existing code" | everything inward-facing only |
| `core/adapters/postgres` (NEW) | Table definitions, generic dataclass<->row mapper, `PgBaseRepository` / `PgOwnerRepository`, per-entity repositories containing only port-specific queries | Postgres via `infrastructure/drivers/pg_engine.py`; ports |
| `core/adapters/postgres/migrations` (NEW) | Alembic baseline + versioned migrations, `powersync` publication, no business logic | Postgres (invoked by a one-shot `migrate` command) |
| `core/infrastructure/drivers/pg_engine.py` (NEW) | Builds the sync SQLAlchemy `Engine`/pool from `PostgresConfig`; lifecycle open/close | adapters/postgres |
| `core/infrastructure/config` (CHANGED) | `AppConfigInterface` gains `datastore` (backend flag) and `postgres` slices; shared `CoreSettings` replaces the duplicated api/scheduler settings; legacy slices become optional | api/scheduler configs |
| `core/infrastructure/containers` (CHANGED) | `RepositoryContainer` becomes the Postgres container (default); `LegacyRepositoryContainer` (current wiring, moved) is swapped in by `bind_datastore()` when `DATASTORE_BACKEND=legacy` | API/scheduler lifespans, `container_dep` |
| `api/auth` (CHANGED) | JWT gets `kid` header (and optional asymmetric alg + JWKS endpoint); new `RefreshSessionRepository` port replaces direct pymongo use; new sync-credentials custom method | PowerSync, mobile |
| `api/v1.py` (CHANGED) | Applies `require_principal` + per-module access policy at router aggregation; one place, testable | resources |
| `api/resources/*` (SMALL ADDITIVE CHANGES) | Optional client-supplied id (AIP-133) and `createTime` on create bodies of offline-writable resources; idempotent create | mobile upload connector |
| PowerSync Service (NEW, self-hosted container) | Reads Postgres WAL, evaluates streams, serves per-user buckets over HTTP/WebSocket; verifies API JWTs | Postgres (replication role), bucket storage, devices |
| `sync/` manifest + generator (NEW, repo root) | Single source of truth: which tables sync, their scope (owner/study/self), writable-from-mobile flag, and their AIP collection/parent. Generates the PowerSync sync config, publication SQL, and Kotlin schema/registry | PowerSync config, migrations, mobile `core:sync` |
| Mobile `core:sync` (NEW module) | `PowerSyncDatabase` factory (expect/actual per platform), generated `Schema`, `ApiBackendConnector` (fetchCredentials + uploadData), sync-status flow, sign-out wipe | `core:data` (HttpClient, token store), feature data modules |
| Mobile `feature:*:data` | `Local*Repository` implementing the feature's domain interface using PowerSync `watch`/`execute`; row<->model mappers | `core:sync`; domain interfaces |

### Data Flow

**Read (server data and wearables to device):**
1. API or scheduler writes through a port to Postgres (`weights` row, or a Fitbit/ActiGraph ingest upsert).
2. Postgres WAL -> PowerSync Service (publication `powersync`, role with `REPLICATION` + `SELECT`).
3. Service evaluates streams per connected user (`WHERE owner = auth.user_id()`), pushes checkpointed deltas.
4. SDK applies deltas into SQLite; `watch()` Flows in `Local*Repository` re-emit; UI updates. Offline: reads are always local.

**Write (offline-first, server authoritative):**
1. Feature use case calls `WeightRepository.record(...)` (domain interface); `LocalWeightRepository` does `INSERT INTO weights (id, owner, weight, created_at, ...) VALUES (uuid(), ...)` in the local DB. The UI updates immediately (optimistic overlay).
2. SDK captures the write in the upload queue (`PUT`/`PATCH`/`DELETE` + table + id + changed columns).
3. When online, `ApiBackendConnector.uploadData()` drains the queue **in order**, maps each op to an AIP call (table below), using the existing authenticated Ktor `HttpClient` (which already does rotating refresh).
4. API validates, authorizes (owner bound to token), stamps `updated_by`/`updated_at`, persists via the port.
5. The write replicates back down through step 2-4 of the read flow; the SDK reconciles the optimistic local row with the server row. **Server value wins** (including normalization). Rejected writes simply never appear in a checkpoint and the optimistic row disappears.

**Auth/sync credentials:**
1. App logs in via `/v1/auth:*` (unchanged); tokens in DataStore.
2. `fetchCredentials()` calls `POST /v1/auth:syncCredentials` through the authenticated client; API returns `{endpoint, token, expiresAt}` where `token` is a freshly minted API access JWT (same claims, `kid` header) and `endpoint` is the configured PowerSync URL. The mobile app therefore needs only the API URL (satisfies "pointable at any server").
3. PowerSync verifies signature/`aud`/`exp` and uses `sub` as `auth.user_id()`.

## Decision 1: Schema strategy -> typed table-per-entity with JSONB only for nested leaves

**Recommendation:** One Postgres table per persisted entity (about 37 tables behind the 37 container providers, not 50: several of the ~50 domain classes are embedded value types such as `StepUpReason`, `StudyWeekDay`, `WeightLost`, `WeightLossProtocol`, `WeightGoalStudyMessage`, `SyncUser` and need triage). Typed columns for every scalar field. `jsonb` only for genuinely nested structures (`User.roles`, `FitbitSleepSession.levels`, `FitbitRecord.distances`, `Session.views`, `ParticipantGroup.pid_to_mid`/`info`, `Admin.groups`, `FitbitHeartRecord` zones, `JobRule` int lists). Optional `extra jsonb` column on tables whose entity is subclassed per study (the entity container explicitly supports per-study subclasses like `F4TJobRule`), so extra subclass fields persist without a migration.

**Why not JSONB documents (one `documents(id, type, data)` table):**
- PowerSync's client schema is per-table SQLite; a single mixed table forces every mobile query through `json_extract` with no useful indexes, and defeats per-table stream scoping and per-table upload mapping.
- The ports are query-driven (`get_for_owner_between`, by-date, by-study, by-email). These need real indexes on `(owner, created_at)`, `(owner, date)`, `study_id`, `email`. JSONB expression indexes would recreate columns the hard way.
- Wearable volume (ActiGraph minute epochs, Fitbit heart records) needs narrow rows and cheap range scans.
- "Fresh start, no ETL" removes the main argument for documents (preserving legacy shapes).
- Entities are mostly flat dataclasses (verified: only ~15 nested `dict`/`list` fields across the whole domain), so JSONB is genuinely the exception.

PowerSync syncs `jsonb` as JSON text and clients read it with `json_extract` (HIGH, official docs); `numeric` syncs as text, so **avoid `numeric`; use `double precision`/`integer`**; `bool` arrives as 0/1; `uuid` and `timestamptz` arrive as text.

**Column conventions (every table):**

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` PK (SQLAlchemy `Uuid(as_uuid=False)` so Python sees `str`) | PowerSync requires a text-compatible `id`; uuid maps to text |
| `owner`, `study_id` (owner entities) | `uuid` nullable FK | Domain defaults are `""`; adapter maps `""` <-> `NULL` (pitfall) |
| `created_at`, `updated_at` | `timestamptz` | Adapter converts domain epoch floats; keeps domain and wire contract unchanged |
| `created_at_tz_offset`, `updated_at_tz_offset` | `integer` | Domain audit metadata, keep |
| `updated_by` | `text` | Stamped by API from the verified principal |
| `deleted_at`, `deleted_by` | `timestamptz`/`text` nullable | Soft delete (Decision 3) |

**Adapter shape (avoid 37 hand-written adapters):** SQLAlchemy 2.x Core (not ORM) + psycopg 3 + Alembic. A generic mapper reflects the dataclass fields against the `Table` (column name = snake_case field name) with codecs for `str<->uuid`, `float<->timestamptz`, `IntEnum<->int`, `dict/list<->jsonb`, `""<->NULL`. `PgBaseRepository[Entity]` implements all of `BaseCrudRepository`; `PgOwnerRepository` adds `get_for_owner(_between)`. A per-entity class exists only for port-specific queries (e.g. `PgGoalRepository.get_all_for_owner_by_kind`). All adapters get the same constructor shape `(engine, entity_type)`, which also fixes the "per-adapter constructor quirks" anti-pattern noted in the codebase map. Reuse the existing `from_domain`/`to_domain` vocabulary only where a table needs a custom codec.

Keep API handlers synchronous (they are `def` routes in the threadpool) so the sync engine fits; use `psycopg_pool` sizing >= threadpool size.

**Hierarchies:** `Goal` (daily/weekly/legacy/kind) and `Condition` (weight/legacy) use a discriminator column (`kind`/`type`) in one table plus typed nullable columns or `extra jsonb` for subtype fields. Do not do table-per-subtype (PowerSync scoping and ports treat them as one collection).

**Natural-key uniqueness for ingestion:** `UNIQUE(owner, fitbit_date)`, `UNIQUE(owner, timestamp_utc)` etc. on wearable tables with `INSERT ... ON CONFLICT DO UPDATE` in `save`, so scheduler re-ingestion is idempotent and does not create duplicate rows that would then sync to devices.

**Query type leakage:** ports are generic over `Query` (N1QL `str`, Mongo `dict`). The API already passes a Mongo-style dict (`user_repo.get_by_query({"email": norm})`) in `auth/service.py`. Replace these with intent methods (`UserRepository.get_by_email`) so Postgres never needs a query dialect. The Postgres `get_by_query(dict)` can still support simple column equality for compatibility.

## Decision 2: Id strategy -> UUID strings everywhere; clients may supply ids

- Domain `BaseEntity.id` is already `str(uuid4())`. Keep it. Postgres stores `uuid`; the Python side sees canonical lowercase hyphenated `str`.
- **ObjectId must leave the domain.** `Participant` carries `bson.ObjectId` for `assigned_coach_id`, `user_id`, `study_id`, and the API hand-rolls `resources/participant.py` to cope. Change these domain fields to `str`; move `ObjectId` coercion into `adapters/mongo/model/mongo_*` (`field_serializer`/validator at the `to_domain`/`from_domain` boundary, which is the fix the codebase map already prescribes). Then delete the hand-rolled participant serializer in favor of `serialize_one`, and `core` no longer needs `bson` for Postgres-only installs. This is a prerequisite for the Postgres adapters and carries legacy-regression risk, so it needs the legacy test suite as its safety net.
- Ids are opaque strings to the API. Path params are validated as UUID at the repository boundary: `get_by_id` of a malformed id returns `None` (-> 404 via existing `EntityNotFoundException`), never a Postgres cast error (500).
- **Offline creates require client-generated ids.** PowerSync generates a UUID locally (`uuid()` in SQLite) and the row is uploaded later. Implement AIP-133 optional user-specified id: `POST /v1/users/{user}/weights?weightId=<uuid>`. Server validates it is a UUID, rejects a collision with a different owner (return the same 409 shape, do not reveal the other owner's row), and treats a repeat create by the same owner as idempotent success (connector falls back to PATCH on 409). This is additive and keeps the wire contract stable.
- Legacy ids (ObjectId hex, Couchbase doc ids) never enter Postgres (fresh start). Under the legacy flag, nothing changes; ids stay opaque strings.

## Decision 3: Soft delete -> `deleted_at` column; synced streams exclude deleted rows

**Legacy semantics today:** `archive` copies the document into an "Archived" type and leaves the original; `delete` route calls `archive`; `unarchive` removes the archive copy; `delete` (purge) hard-deletes. This is not a flag and cannot be mirrored in a relational table literally.

**Postgres semantics:**
- `archive(id)` -> `UPDATE ... SET deleted_at = now(), deleted_by = :principal WHERE id = :id AND deleted_at IS NULL`
- `unarchive(id)` -> `SET deleted_at = NULL`
- `delete(id)` (`:purge`) -> hard `DELETE` (idempotent)
- Default reads (`list_all`, `get_for_owner*`, `get_by_query`) filter `deleted_at IS NULL`.
- `get_by_id` must be able to see archived rows because `:undelete` and `:purge` call `_fetch` first. Add a keyword `include_archived: bool = False` to `BaseCrudRepository.get_by_id` (legacy adapters accept and ignore it because their originals stay in place) and have the undelete/purge handlers pass `True`. Optionally add nullable `deleted_at` to `BaseEntity` so the API can emit AIP-164 `deleteTime`; legacy leaves it `None` (additive wire field).

**Sync representation:** the stream query includes `AND deleted_at IS NULL`. When the server sets `deleted_at`, the row leaves the user's bucket and PowerSync removes it from the device (VERIFY with a spike: official docs confirm streams filter with static conditions, but I did not find a doc page that states the exact remove-on-filter-transition behavior). Undelete re-adds it; purge removes it from the WAL. Devices never receive tombstones and never need `deleted_at` in their schema. A local delete on the device is a real `DELETE` in SQLite -> `DELETE` op in the queue -> `DELETE /v1/...` -> server `archive`. This is consistent: the row is already gone locally and gone from the stream.

Include `deleted_at` in the **baseline migration** (PowerSync docs warn that adding a column and relying on it for existing rows does not propagate automatically and changing filter-relevant values via ALTER TABLE is not replicated reliably). Any future backfill must be an explicit `UPDATE` touching every affected row.

## Decision 4: Backend selection seam -> swap the repository sub-container at the composition root

**Verified experimentally (dependency-injector 4.49.1, the locked version):**
- `providers.Factory("dotted.path.Class")` string imports are resolved **eagerly at Factory construction**, so they do not give lazy loading. Importing both adapter families at module import stays a problem (the current `repository_container.py` imports Couchbase and Mongo adapters at the top, so the Couchbase SDK loads even for Postgres).
- `container.repositories.override(providers.Container(OtherRepositoryContainer, app_config=..., entities=...))` works: `getattr(container.repositories, "weight")()` then resolves from the overriding container, and a later `container.repositories.weight.override(...)` (the test seam) still works.

**Therefore:**
1. Move the current `RepositoryContainer` body to `containers/legacy_repository_container.py` as `LegacyRepositoryContainer` (unchanged wiring and kwarg quirks, plus the Couchbase/Mongo driver providers).
2. New `containers/repository_container.py` holds the **Postgres** `RepositoryContainer` with identical provider names (one per port). It imports only `adapters/postgres` and the PG driver.
3. Add `bind_datastore(container, config)` in `containers/datastore.py`:
   ```python
   def bind_datastore(container: BaseContainer, config: AppConfigInterface) -> None:
       container.app_config.override(providers.Object(config))
       if config.datastore.backend == "legacy":
           from .legacy_repository_container import LegacyRepositoryContainer  # lazy import
           container.repositories.override(providers.Container(
               LegacyRepositoryContainer,
               app_config=container.app_config, entities=container.entities))
   ```
   API lifespan and scheduler `celery_app.py` call it instead of `container.app_config.override(...)`.
4. A **lifecycle provider** replaces the Couchbase-specific calls (`entity_repository().initialize()`/`cleanup()` in the API lifespan, `worker_process_init` in the scheduler). `datastore.open()`/`close()` is implemented by `PostgresLifecycle` (build pool, verify Alembic head, fail fast if behind) and `LegacyLifecycle` (current Couchbase init). The Mongo refresh-collection wiring (`collection_repository()[...]`) moves behind the new `RefreshSessionRepository` port.
5. **Parity guard:** a unit test asserts `set(PgRepositoryContainer.providers) == set(LegacyRepositoryContainer.providers)`, so a new port cannot be added to one backend only.
6. Move `couchbase` and `pymongo` to an optional extra (`openwellness-core[legacy]`); the Docker `api`/`scheduler` targets install the default (Postgres) set, with a documented `legacy` build arg. This also shrinks the self-host image.

`DATASTORE_BACKEND=postgres|legacy` lives in a shared `core` `DatastoreSettings`; Couchbase/Mongo settings classes are only instantiated when `legacy` is selected, so a Postgres deployment does not require `COUCHBASE_URL`/`MONGO_URL`. Consolidating `AppConfig` into `core` (already an Active requirement) removes the api/scheduler duplication.

**Auth persistence:** `api/auth/session_store.py` takes a pymongo `Collection` and uses Mongo CAS (`update_one({_id, rotatedAt: None, revoked: False})` + `matched_count`). Introduce a `RefreshSessionRepository` port (in `core/application`) exposing the atomic primitives (`insert`, `consume_if_unrotated(hash) -> bool`, `revoke_family`, `revoke_user`, `find`). `PgRefreshSessionRepository` uses `UPDATE ... WHERE rotated_at IS NULL AND NOT revoked RETURNING`; `MongoRefreshSessionRepository` wraps existing logic. The reuse-detection policy stays in the API's `RefreshSessionStore`. The `refresh_sessions` table is **not** in the PowerSync publication (token hashes must not enter the sync service).

## Decision 5: Auth at the router, owner binding, PowerSync JWT reuse

- **Enforce once, at aggregation.** In `v1.py`, `v1.include_router(mod.build_router(), dependencies=[Depends(require_principal)])` for every `RESOURCE_MODULES` entry; `auth.build_router()` stays outside. Flip `enforce_principal` default to `True` and remove the `X-Principal-Id` trust in `get_principal`. Each resource module exposes an `ACCESS` constant (`OWNER_SCOPED`, `ADMIN_ONLY`, `COACH_READ`, `STUDY_SCOPED`, ...) that `v1.py` turns into additional dependencies. A test iterates `RESOURCE_MODULES` and fails if a module lacks `ACCESS` or if an anonymous call to any route is not 401 (the test CONCERNS.md recommends).
- **Owner binding** is a router-level dependency on the `/users/{user}/...` prefix: non-admin callers need `principal.id == user`, else **404** (keeps the existing "never reveal exists" convention in `check_parent`); roles gate with 403. Coach access to a participant's data requires a lookup (`participant.assigned_coach_id`); keep coach scope read-only in v1 unless the requirements say otherwise.
- **Invariant shared by API and sync:** "a user may only see/write rows where `owner == token.sub`." The PowerSync stream predicate and the API owner binding must stay identical. Add a contract test in the sync phase that checks both against the same fixtures.
- **Confirm the owner meaning** (open question): the JWT has `sub` (user id) and `participant` (pid). Path is `/users/{user}` and the weights test uses `owner == "user-1"`, so `owner` appears to be the user id, which makes streams a simple `owner = auth.user_id()`. If any legacy semantics make `owner` the participant id, scoping must use the `participant` claim instead.
- **PowerSync accepts custom JWTs** with required `kid` header, `sub`, `aud` in `client_auth.audience`, `iat`+`exp` (max 24h, recommend <= 60 min; API's 15 min qualifies) (HIGH, official docs). **HS256 shared secret is documented as dev/testing only**; production should use a JWKS (RSA/EdDSA/ECDSA) via `client_auth.jwks_uri` or static `jwks.keys`.
  - Recommendation: add `kid` to minted tokens now (cheap, backward compatible); support `API_AUTH_JWT_ALG` of `HS256` (default for local compose, PowerSync `kty: oct` key) or `ES256`/`EdDSA` with a private key and a `/.well-known/jwks.json` endpoint for production; make the deployment guide mandate the asymmetric mode. `token_service.py` already isolates JWT crypto and has `jwt_alg` configurable, so this is a contained change. It must land in the auth phase, before PowerSync wiring, because it changes the secrets story documented in `.env.example`.
  - Add `powersync` to `client_auth.audience` alongside the existing audience, or mint the sync token with `aud` = a dedicated value in `auth:syncCredentials`. Prefer the dedicated minted token (the API access token is not handed to a second service), still signed by the same key and carrying the same `sub`/`roles`.

## Decision 6: Mobile local DB inside the KMP clean-architecture modules

Existing graph: `core:{domain,data,presentation}`, `feature:auth:{domain,data,presentation}`, `shared` wires Koin, Ktor 3.5.0, Koin 4.1.0, Kotlin 2.3.21.

```
:core:domain            (unchanged: pure Kotlin)
:core:data              (unchanged: HttpClient, AuthTokenStorage)
:core:sync       NEW    depends on :core:domain, :core:data
                         - PowerSyncDatabase factory (expect/actual DatabaseDriverFactory: Android needs Context)
                         - GeneratedSchema.kt (from sync manifest)
                         - ApiBackendConnector (fetchCredentials -> POST auth:syncCredentials; uploadData -> registry)
                         - UploadRegistry (table -> AIP path/method/field codec), generated from manifest
                         - SyncStatus flow, connect()/disconnectAndClear() lifecycle
                         - Timestamps codec (single place to parse PowerSync timestamptz text)
:feature:<name>:domain  models, repository interface, use cases (no PowerSync types)
:feature:<name>:data    Local<Name>Repository (db.watch / db.execute), row<->model mappers
:feature:<name>:presentation
:shared                 Koin: coreDataModule + coreSyncModule + feature modules
```

- **Dependency rule preserved:** feature `domain` knows nothing about PowerSync. Only `feature:*:data` and `core:sync` import `com.powersync`. Presentation depends on use cases only.
- **Why a separate `:core:sync` rather than adding to `:core:data`:** it carries a heavy native SQLite dependency and platform actuals, is sign-in scoped, and lets `:feature:auth` stay free of it.
- **Query layer:** use PowerSync's native `watch`/`execute` first. The SQLDelight integration (`com.powersync:integration-sqldelight`) is documented as beta and requires async-only generation, `sqlite-3-38` dialect, `linkSqlite=false`, starting schema versioning at 2, and per-module generated database types; defer it. (MEDIUM; docs.)
- **Lifecycle:** `connect(connector)` after successful login/registration and on app start with stored tokens; `disconnectAndClear()` on logout/revoke so health data does not persist on the device after sign-out. Hook this into the existing auth feature's sign-out use case via a small `core:domain` interface (`SessionLifecycle`) implemented in `core:sync`, so `feature:auth` does not depend on `core:sync`.
- **Write-gating:** `feature` domain interfaces simply do not expose writes for server-ingested tables (Fitbit/ActiGraph records are download-only). The generated manifest marks them `writable: false` and the connector rejects any queued op for them defensively.
- **Platform/tooling risk (VERIFY):** the Kotlin SDK (`com.powersync:core`) supports Android, JVM and Apple targets, and the repo uses AGP 9.0.1 with the new `androidMultiplatformLibrary` plugin and Ktor 3.5.0. Confirm SDK compatibility with these versions and with PowerSync's own bundled Ktor before committing the module structure.

## Decision 7: Upload path -> AIP endpoint mapping

PowerSync queues ops as `PUT` (create/replace), `PATCH` (changed columns), `DELETE` (id only) per table (HIGH). The connector maps by registry (generated from the manifest):

| Local op | AIP call | Notes |
|----------|----------|-------|
| `PUT` weights/{id} | `POST /v1/users/{me}/weights?weightId={id}` body from row (camelCase via codec) | `{me}` = current user id (from token store); DELETE ops carry no owner so the registry always uses the signed-in user for owner-scoped tables. On `409` -> `PATCH` instead. |
| `PATCH` weights/{id} | `PATCH /v1/users/{me}/weights/{id}` with only changed fields | Matches the existing update-mask convention (`exclude_unset`). |
| `DELETE` weights/{id} | `DELETE /v1/users/{me}/weights/{id}` | Server archives (soft delete). `404` treated as already deleted. |
| local "restore" | `POST .../{id}:undelete` | Not needed from mobile in v1; coach/admin do it via dashboard. |
| (purge) | never from mobile | `:purge` is admin/dashboard only. |

Rules:
- **Process one local transaction at a time, entries in order** (create before patch), complete the transaction only after all calls succeed.
- **Do not treat 4xx as retryable.** PowerSync docs warn that an unresolved failure blocks the upload queue indefinitely and recommend not returning 4xx for validation problems (HIGH). Because our API is a normal REST API that must keep returning 4xx, the connector converts non-retryable results (400/403/404/409-unresolvable/422) into: record a row in a local-only `upload_rejections` table (surfaced in UI/diagnostics), call `complete()`, continue. Network errors, 5xx and 401-after-refresh failure throw so the SDK retries with backoff.
- **Idempotency:** client ids + 409->PATCH fallback make retries safe after partial success or lost responses.
- **Server must apply writes synchronously** before responding (docs: do not queue writes for later or they flicker out of the next checkpoint). The existing sync `def` handlers already do this.
- **Measurement time:** domain `created_at` on owner entities is the measurement time (`Weight` docstring). Current create bodies (`WeightCreate`) carry no timestamp, so a delayed offline upload would be stamped with upload time. Add an optional `createTime` (RFC-3339) to create bodies of offline-writable resources, honored only on create and bounded sanity-checked (reject far-future). Also carry `createdAtTzOffset`. Additive, wire-compatible.
- **Uploadable subset:** only tables a participant legitimately writes (weights, goals if participant-editable, daily_state, food/sleep/stress logs, survey results, physical activity, participant messages, user settings). Everything else is download-only.
- **Unknown-field safety:** wire schemas use `extra="ignore"`, so a newer client sending extra fields to an older server will not 400.

## Sync scoping (PowerSync Sync Streams)

Use **Sync Streams** (current recommended mechanism; `config: edition: 3`, `streams:`, `auto_subscribe: true`). Sync Rules are the legacy path (HIGH from docs index; exact deprecation date not stated). Scope classes defined in the manifest:

| Scope | Predicate | Tables (examples) |
|-------|-----------|-------------------|
| `owner` | `owner = auth.user_id() AND deleted_at IS NULL` | the 30 `BaseOwnerEntity` tables: weights, goals, daily_states, user_foods, user_sleeps, user_stresses, survey_results, physical_activities, messages, user_settings, Fitbit/ActiGraph records |
| `self` | `id = auth.user_id()` / `user_id = auth.user_id()` | the participant's `users` and `participants` rows |
| `study` | `study_id IN (SELECT study_id FROM participants WHERE user_id = auth.user_id())` | studies, study_settings, job_rules, cards, assets, study_messages (read-only reference data) |
| `none` | not synced | admins, apps, devices (unless needed), refresh sessions, anything auth-related |

Notes:
- Subqueries via `IN (SELECT ...)` are supported by Sync Streams (HIGH). Filtering only on a client `subscription.parameter(...)` without an `auth.user_id()` check would let a client request any value; every stream must be anchored to the token.
- Combine tables with the same scope into one stream's `queries:` list to keep per-user bucket count down (docs mention a per-user bucket limit; value not stated, VERIFY).
- **High-volume wearable windows:** minute-level ActiGraph and Fitbit heart data will not fit "sync everything forever". Use a client-supplied lower-bound parameter for those streams (PowerSync has a "sync data by time" pattern; VERIFY exact syntax in the sync phase). Daily aggregates sync in full. This is the one place the "sync full participant-scoped data" requirement needs a pragmatic carve-out.
- Publication is explicit: `CREATE PUBLICATION powersync FOR TABLE <manifest-synced tables>` generated from the manifest (not `FOR ALL TABLES`, which the docs warn can cause memory spikes, and which would leak auth tables).
- Postgres requirements (HIGH): version >= 11 (use 16+), `wal_level=logical`, role with `REPLICATION BYPASSRLS` + `SELECT` on synced tables, publication named `powersync`. Bucket storage can be MongoDB or Postgres (Postgres storage supported from service v1.3.8); use **Postgres bucket storage in a second database on the same server** (Postgres >= 14 can co-host replication source and bucket storage; below 14 they need separate servers) so new deployments need no MongoDB.
- Server-ingested wearable data needs no sync code: the scheduler writes through ports; WAL does the rest.

## Required changes to existing code (summary)

| Area | Change | Why |
|------|--------|-----|
| `domain/models/participant.py` and Mongo models | `ObjectId` -> `str` in domain; coercion moves into `adapters/mongo/model` | Postgres uuid FKs; removes `bson` from domain; deletes hand-rolled participant router |
| `BaseCrudRepository` | `get_by_id(..., include_archived=False)` | `:undelete`/`:purge` on soft-deleted rows |
| `UserRepository` and similar | Intent methods (`get_by_email`) replacing `get_by_query({"email": ...})` | No dialect leakage into API |
| `AppConfigInterface` | `datastore`, `postgres` slices; legacy slices optional; shared `CoreSettings` | Backend flag, config consolidation |
| `containers/*` | Split legacy vs Postgres repository containers; `bind_datastore`; lifecycle provider | Selection seam |
| `api/main.py` lifespan, `celery_app.py` | Use `bind_datastore` + `datastore.open()/close()` | Remove Couchbase-specific calls |
| `api/auth/session_store.py` | Behind `RefreshSessionRepository` port | Postgres auth persistence |
| `api/auth/token_service.py` | `kid` header, optional asymmetric alg, JWKS route, `auth:syncCredentials` | PowerSync auth |
| `api/v1.py`, `deps/principal.py` | Router-level `require_principal`, `ACCESS` policies, owner binding; drop `X-Principal-Id` trust | Security milestone |
| Owner-scoped create schemas/routes | Optional `{resource}Id` query param and `createTime` | Offline creates |
| `docker-compose.yml` | `postgres` (logical WAL), one-shot `migrate`, `powersync`, init SQL for role/second DB | Self-host kit |

## Patterns to Follow

### Pattern 1: Manifest-driven synced-table contract
**What:** `sync/manifest.yaml` lists each synced table with `scope`, `writable`, and `api: {collection, parent}`. A generator emits `sync-config.yaml`, the publication migration fragment, Kotlin `GeneratedSchema.kt` and `UploadRegistry`. A pytest compares manifest tables/columns to SQLAlchemy metadata; CI fails on drift (generated files checked in).
**When:** From the first synced table. Three hand-maintained copies of ~35 table definitions (Postgres, PowerSync YAML, Kotlin) will drift.
**Example:**
```yaml
weights:
  scope: owner
  writable: true
  api: { collection: weights, parent: users }
fitbit_records:
  scope: owner
  writable: false
  api: { collection: fitbitRecords, parent: users }
```

### Pattern 2: Container swap at the composition root
**What:** `bind_datastore()` overrides `repositories` with the legacy sub-container only when selected; default container imports no Couchbase/Mongo code.
**When:** Always; keep `container_dep` and test overrides untouched.

### Pattern 3: Contract tests per port, run against every backend
**What:** One parametrized suite per port (create/get/list/between/archive/unarchive/purge/ownership) runs against the in-memory fake (always), Postgres via a containerized instance (marked `integration`), and optionally legacy. Existing suites stay infrastructure-free as required.

### Pattern 4: Local repository over a flow
**What:** `Local<Name>Repository` exposes `Flow<List<Model>>` from `db.watch(sql, params) { mapper(it) }` and `suspend` write methods that issue local SQL only; no network in the feature layer.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Letting PowerSync or the app write Postgres directly
**Why bad:** Bypasses validation, owner binding, audit stamping, and the wire contract.
**Instead:** Device -> upload queue -> API only. The PowerSync DB role is read-only.

### Anti-Pattern 2: Document-store-in-Postgres
**Why bad:** Recreates Couchbase's lack of schema while losing Couchbase's tooling; hurts mobile queries and indexing.
**Instead:** Typed tables, JSONB only for nested leaves.

### Anti-Pattern 3: `FOR ALL TABLES` publication
**Why bad:** Replicates refresh-session hashes and auth tables into the sync service; docs warn of memory/lag on large volumes.
**Instead:** Publication generated from the manifest.

### Anti-Pattern 4: Returning retryable failure for validation errors in the connector
**Why bad:** A single bad row blocks all later uploads.
**Instead:** Classify errors, record rejection, `complete()`.

### Anti-Pattern 5: Auto-running Alembic at API startup
**Why bad:** Races between api, scheduler, and PowerSync startup; PowerSync reading a half-migrated schema.
**Instead:** One-shot `migrate` service/command; services verify head and fail fast; PowerSync `depends_on` migrate completion.

### Anti-Pattern 6: Two JWT trust models
**Why bad:** A separate sync auth system doubles the secrets story.
**Instead:** One signing key family; PowerSync verifies via the same JWKS (or HS256 in dev).

## Scalability Considerations

| Concern | Lab scale (tens to hundreds of participants, single VM) | Thousands | Beyond |
|---------|-----------------------------------|-----------|--------|
| Wearable row volume | Plain tables with `(owner, timestamp)` indexes; window the sync | Partition ActiGraph/heart tables by month (check PowerSync publication behavior with partitions, VERIFY) | Out of scope (single VM target) |
| Buckets per user | ~35 streams; merge same-scope tables | Same | Review PowerSync limits |
| List endpoints | `list_all` + in-memory `paginate` is acceptable | Add keyset pagination at the port | Out of scope |
| Connections | One sync stream per device; Compose sizing documented | Raise pool sizes | Out of scope |
| Replication | Single Postgres with logical replication | Same | Managed Postgres / read replica for replication |

## Suggested Build Order (dependencies drive phases)

1. **Foundation refactors (no behavior change)**: ObjectId out of domain; `include_archived`; `get_by_email`; `RefreshSessionRepository` port with Mongo adapter; shared `CoreSettings` and `datastore` config; legacy/Postgres container split with `bind_datastore` (Postgres container initially empty/stub). Gate: existing suites green.
2. **Security enforcement (parallel with 3)**: router-level `require_principal`, `ACCESS` policies, owner binding, role gates, anonymous-401 test over `RESOURCE_MODULES`; JWT `kid`/alg/JWKS groundwork. Independent of Postgres; must precede production docs.
3. **Postgres core**: engine and lifecycle, Alembic baseline and the `migrate` command, generic mapper and base repositories, `users`/`participants`/`studies`/`apps`/`admins`/`refresh_sessions` so OTP login and registration work end to end on Postgres (first vertical slice), then Weight as the owner-scoped pilot, then remaining families in batches (owner-scoped 30, study-scoped, Fitbit/ActiGraph with natural keys), each batch gated by the shared port contract suite.
4. **Parity and selection hardening**: provider-name parity test, legacy-flag smoke, optional `legacy` extra, Docker targets.
5. **Wire additions for offline writes**: AIP-133 client ids, idempotent create, `createTime`/tz offset on create bodies. Lands before mobile upload work, after the Postgres base repository exists.
6. **PowerSync server**: compose service and Postgres storage database, replication role and generated publication, manifest and generator, stream scopes, `auth:syncCredentials`, key/`kid` config. Validate with a headless client or the PowerSync diagnostics tool against a seeded Postgres before mobile.
7. **Mobile `core:sync`**: driver factory per platform, generated schema, connector, status, sign-out wipe. Then one vertical feature (weights) proving create/edit/delete offline -> reconnect -> upload -> server round trip. Then expand per family.
8. **Self-host kit and docs** build on 3 to 7 (the kit's `.env.example`, bootstrap seed, compose, and docs describe the final stack).

Sequencing note: step 6 depends on both 3 (tables to publish) and 2 (token format); step 7 depends on 5 and 6. Steps 2 and 3 are parallelizable.

## Open Questions / Gaps

- **`owner` semantics (user id vs participant id)** in owner-scoped entities and legacy data: assumed user id from the path and tests; confirm before writing stream predicates.
- **Archive/undelete product semantics** for legacy retention: legacy `delete` only copies; is a restore window or purge policy required?
- **Sync-removal-on-soft-delete** and `timestamptz` text format on the client (`T` vs space separator): needs a spike with a real PowerSync instance.
- **Kotlin SDK compatibility** with AGP 9.0.1, Kotlin 2.3.21, Ktor 3.5.0, and the `androidMultiplatformLibrary` plugin (VERIFY first thing in the mobile phase).
- **Bucket/stream limits and windowing syntax** for wearable streams.
- **Entity inventory triage** (which of the ~50 domain classes are persisted tables vs embedded types vs legacy-only like `SyncUser`).
- **Coach authorization model**: coach access to participants (assignment via `assigned_coach_id`) needs a policy decision.

## Sources

- Codebase (HIGH, read directly): `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`; `backend/core/src/openwellness_core/{domain/models, application/repositories, adapters, infrastructure/containers, infrastructure/config}`; `backend/api/src/openwellness_api/{main.py, v1.py, deps/principal.py, auth/token_service.py, auth/session_store.py, resources/weight.py, resources/participant.py, common/handlers.py, schemas/weight.py}`; `frontend/mobile/{settings.gradle.kts, gradle/libs.versions.toml, core/data/...}`.
- Experiment (HIGH): dependency-injector 4.49.1 string-import eagerness and `providers.Container.override` behavior, run in a throwaway environment.
- PowerSync custom auth, JWT claims, HS256 dev-only, `fetchCredentials` flow: https://docs.powersync.com/installation/authentication-setup/custom (HIGH, official)
- PowerSync Sync Streams overview and query rules (`auth.user_id()`, `subscription.parameter`, subqueries, joins, `edition: 3`): https://docs.powersync.com/sync/streams/overview , https://docs.powersync.com/sync/streams/queries (HIGH, official)
- PowerSync Kotlin SDK reference (targets, schema, connector, SQLDelight/Room): https://docs.powersync.com/client-sdks/reference/kotlin (HIGH, official); SQLDelight integration (beta, limits): https://docs.powersync.com/client-sdks/orms/kotlin/sqldelight (HIGH)
- PowerSync client write handling (PUT/PATCH/DELETE, synchronous server apply, avoid 4xx): https://docs.powersync.com/handling-writes/writing-client-changes.md (HIGH, official)
- PowerSync Postgres source setup (wal_level, REPLICATION role, `powersync` publication, version): https://docs.powersync.com/configuration/source-db/setup (HIGH, official)
- PowerSync type mapping and JSON handling: https://docs.powersync.com/sync/types , https://docs.powersync.com/client-sdks/advanced/custom-types-arrays-and-json.md (HIGH for jsonb/text and numeric/text; timestamp format MEDIUM via search snippet)
- PowerSync self-hosting, bucket storage (MongoDB or Postgres >= service 1.3.8): https://docs.powersync.com/configuration/powersync-service/self-hosted-instances , https://github.com/powersync-ja/self-host-demo (MEDIUM, search summary)
- PowerSync schema-change caveats (column additions/filters): https://docs.powersync.com/maintenance-ops/implementing-schema-changes (MEDIUM, search summary)
- Not found in docs (so treated as VERIFY): exact remove-on-filter-transition behavior for soft deletes; bucket-count limit values; Kotlin SDK version matrix.
