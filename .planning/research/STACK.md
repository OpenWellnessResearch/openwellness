# Stack Research

**Domain:** Self-hostable research-study platform: Postgres persistence behind existing repository ports, PowerSync offline-first sync to a KMP app, one-command self-host kit
**Researched:** 2026-10-29
**Confidence:** MEDIUM-HIGH (versions verified against PyPI, Maven Central, Docker Hub, GitHub tags/releases and official docs.powersync.com; a few PowerSync behaviors are doc-only and flagged for a spike)

Scope: only the NEW stack for this milestone. The existing system (Python 3.12/uv, FastAPI, Celery/Redis, React 19/Vite, Kotlin 2.3.21, Compose MP 1.11, Ktor 3.5, Koin) is in `.planning/codebase/STACK.md` and is not re-researched.

Verification note: Context7 MCP tools were not available in this session. Versions were verified directly from PyPI JSON, Maven Central metadata, Docker Hub tag API, GitHub release/tag files (`powersync-kotlin` `gradle/libs.versions.toml` per tag), and the official PowerSync / SQLAlchemy / Mailpit / testcontainers docs. Each row carries a confidence level.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| PostgreSQL | 18 (`postgres:18`, 18.6 current; 17 is an acceptable fallback) | System of record + PowerSync replication source | PowerSync's own self-host demo runs `postgres:18`; supported to 2030-11. Needs `wal_level=logical` (see below). NOTE: PG18 images moved the data dir, so mount the volume at `/var/lib/postgresql` (not `/var/lib/postgresql/data`). | HIGH |
| SQLAlchemy **Core** (not ORM) | `>=2.1.6,<2.2` | Table definitions, query building, connection pooling | Domain entities are plain `@dataclass`es and the codebase already has a separate persistence-model layer per adapter (e.g. `CBFitbitWeight`). ORM mapping/identity-map/unit-of-work would duplicate that and fight the repository-port style. Core gives typed `Table`s, safe dynamic WHERE building for the AIP `filter=` feature, `JSONB`, and feeds Alembic autogenerate. 2.1 defaults `postgresql://` to psycopg 3, requires Python 3.11+ (project is 3.12). 2.1 breaking changes (autoflush, `filter_by`, composites, dataclass defaults) are ORM-side and do not touch Core-only usage. | HIGH |
| psycopg (v3) `[binary]` | `>=3.3.6,<3.4` | Postgres driver, **sync** | SQLAlchemy 2.1 default driver; actively maintained; use `postgresql+psycopg://`. `[binary]` avoids needing libpq-dev in the `python:3.12-slim-bookworm` image. | HIGH |
| Alembic | `>=1.20.1,<1.21` | Versioned, reproducible schema migrations (incl. the `powersync` publication) | De-facto SQLAlchemy migration tool; supports Core `MetaData` autogenerate; latest requires `SQLAlchemy>=2.0`. Spike to confirm against SA 2.1 on day 1 (no known issue found). Put `alembic/` + `MetaData` in `core` so api and scheduler share one schema. | MEDIUM-HIGH |
| PowerSync Service (Open Edition) | Docker image `journeyapps/powersync-service:1.27.2` (pin the tag, never `latest`) | Replicates Postgres to per-user buckets and streams to clients | Official self-host image (Docker Hub, updated 2026-10-24). Single container runs API + replication (`start -r unified`). Sync Streams need service >= 1.20. | HIGH |
| PowerSync bucket storage | **Postgres** (`storage.type: postgresql`), separate database `powersync_storage` + dedicated role on the same Postgres 18 server | PowerSync's own bucket/oplog storage | Avoids adding a MongoDB replica set (extra container + one-time `rs.initiate` step) to a stack that is deliberately dropping Mongo. Status is **Beta** ("production-ready if you've adequately tested your use case", parity with Mongo storage). Same-server use is documented as supported only on Postgres > 14 (we are on 18). Fallback if the spike shows problems: a second small `postgres:18` container (this is exactly the official `nodejs-postgres-bucket-storage` demo topology). | MEDIUM |
| PowerSync Sync Streams | `config: edition: 3`, `auto_subscribe: true` | Declares which rows each device receives | Sync Rules are officially "deprecated, being phased out in favor of Sync Streams". Use Streams from day one so there is no migration later. `auto_subscribe: true` reproduces the old "sync everything upfront" behavior needed for offline-first parity. | HIGH |
| PowerSync Kotlin SDK `com.powersync:core` + `com.powersync:compose` | **1.14.1** now; **1.15.2** after the Kotlin toolchain bump (see Version Compatibility) | Local SQLite + sync client + upload queue for the KMP app (Android + iOS) | Official KMP SDK; Android/JVM/Apple targets; Ktor (OkHttp/Darwin) for networking (same engines the app already uses); SQLite core is statically linked on Apple targets since 1.12.0 (no Swift package/CocoaPod needed). 1.14.1 was built with Kotlin 2.3.21 + Compose MP 1.11.1 + Ktor 3.5.0, an exact match for this repo's toolchain. Note the Maven artifact is `com.powersync:compose` (docs sometimes write `powersync-compose`). | HIGH (versions) / MEDIUM (iOS runtime behavior, not exercised) |
| Mailpit | `axllent/mailpit:v1.32` (v1.32.0, 2026-10-22) | Dev SMTP catcher + web UI + REST API | Actively maintained (MailHog is abandoned). SMTP on 1025, UI/API on 8025. Its REST API lets the README-verification script fetch the OTP programmatically. | HIGH |
| testcontainers-python | `testcontainers>=4.15,<5` | Real-Postgres integration tests | Current (4.15.0); `PostgresContainer` module. Pass `driver="psycopg"` (constructor default is `psycopg2`) so the URL is `postgresql+psycopg://...`. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyjwt[crypto]` (already in project) | existing `>=2.9,<3` (latest 2.15.1) | Mint the separate PowerSync token (EdDSA/RS256 or HS256) with `kid` header | Always; no new dependency. `jwt.encode(claims, key, algorithm="EdDSA", headers={"kid": ...})`. |
| `cryptography` (via `pyjwt[crypto]`) | existing | Generate/serialize the Ed25519 or RSA signing key and the JWKS document | Bootstrap command + `/.well-known` JWKS route. |
| `psycopg-pool` | 3.3.3 | psycopg-native pool | **Skip.** Use SQLAlchemy's built-in `QueuePool` (see sizing note). |
| `com.powersync:connector-supabase` | n/a | Supabase connector | **Do not add.** We upload through our own API. |
| PowerSync CLI (`powersync`) | latest | Scaffold/validate sync config, `migrate sync-rules` | Optional dev tool; not required by the kit. |
| Caddy or nginx | latest stable | TLS reverse proxy in the single-VM deployment guide | Deployment phase only. PowerSync service needs its own host/subdomain and TLS for real phones. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` marker `integration` + session-scoped `PostgresContainer("postgres:18", driver="psycopg")` fixture | Postgres adapter tests | Fixture runs `alembic upgrade head` once; per-test isolation via transaction rollback or `TRUNCATE`. Auto-skip when Docker is unavailable so the existing infra-free suites still pass with a bare `pytest`. |
| Mailpit REST API (`GET :8025/api/v1/messages`) | Extract OTP in e2e/README verification | Replaces scraping the UI. |
| `docker compose` one-shot `migrate` service | Run `alembic upgrade head` | `api`/`scheduler` use `depends_on: {migrate: {condition: service_completed_successfully}}`. |
| Postgres `docker-entrypoint-initdb.d` script (`.sh`, reads env) | First-boot: create `powersync_role`, `powersync_storage` DB/role | Runs only on an empty data dir; publication is created by Alembic (see below), not by init SQL. |

## Detailed Findings by Question

### 1. Postgres access in the Python backend

**Decision: SQLAlchemy 2.1 Core + psycopg 3 (sync) + Alembic.**

- **Sync, not async.** All ~41 repository ports are sync, the ~360 FastAPI handlers in `resources/` are sync `def` (run in Starlette's threadpool), and Celery tasks are sync. An async engine (asyncpg / `psycopg` async) would require either rewriting every port or `run_sync` bridges. Sync gives the same behavior in api, scheduler, bootstrap CLI, and Alembic with one engine factory in `core`.
- **Core over ORM.** One generic `PgRepository[Entity]` base (table + `to_row`/`from_row`, mirroring `CBBaseRepository` with its `persistence_type`) plus ~41 thin subclasses for owner/date-range queries. ~50 `Table` definitions in one `MetaData` live in `core/adapters/postgres/`.
- **Not psycopg directly.** You would hand-roll dynamic WHERE building for `filter=`, lose Alembic autogenerate, and lose dialect-safe identifier/param handling. The repo already enforces a "no f-string N1QL" lint (`check_no_fstring_n1ql.py`); Core's bound parameters make the equivalent guarantee structural.
- **Pooling.** `create_engine(url, pool_size=10, max_overflow=10, pool_pre_ping=True)` per process. FastAPI's threadpool defaults to 40 threads x 2 uvicorn workers; size the pool deliberately and document `PG_POOL_SIZE` in the env reference. Total connections = (api workers x (pool+overflow)) + scheduler + PowerSync (default `max_pool_size` 8) + storage; stay under Postgres `max_connections=100`.
- **Schema rules driven by PowerSync (these are stack constraints, decide them in the schema phase):**
  - Every synced table needs a text-compatible `id` primary key. Entities use `str(uuid4())` ids and legacy ids may not be valid UUIDs, so use `text` (or `uuid` only where guaranteed). PowerSync maps `uuid`->text.
  - Postgres -> SQLite type mapping: `timestamptz`->ISO text, `jsonb`/arrays/`numeric`->text (JSON arrays for arrays), `bool`->integer, `float8`/`float4`->real, ints->integer. Domain `created_at`/`updated_at` are float epoch seconds; keep them `double precision` to preserve the `/v1` wire contract and avoid string-time handling on device.
  - Do NOT put refresh-session hashes or other auth secrets in the `powersync` publication.
- **Publication management.** Create `powersync_role` in the init script; create/alter the publication **in Alembic migrations with an explicit table list** (`CREATE PUBLICATION powersync FOR TABLE ...`, `ALTER PUBLICATION powersync ADD TABLE ...` in each migration that adds a synced table). Do NOT use `FOR ALL TABLES` outside a dev toy: PowerSync reads every change in the publication (memory/lag), and it would replicate auth/OTP-adjacent tables into bucket storage. Grant `SELECT` to `powersync_role` only on synced tables.
- **Backend selection flag.** Keep `DATASTORE_BACKEND=postgres|legacy` (name TBD in architecture phase) resolved in the `core` DI container; `sqlalchemy`/`psycopg` become base dependencies of `core`, `couchbase`/`pymongo`/`requests` become an optional extra (`core[legacy]`) so the default install and image are lighter and Postgres-only labs never need the Couchbase SDK wheel.

### 2. Self-hosted PowerSync service

**Postgres source requirements (official docs, HIGH):**

```sql
-- postgres started with: -c wal_level=logical   (compose: command: ["postgres","-c","wal_level=logical"])
CREATE ROLE powersync_role WITH REPLICATION BYPASSRLS LOGIN PASSWORD '...';
GRANT SELECT ON <synced tables> TO powersync_role;      -- or ALL TABLES IN SCHEMA public + ALTER DEFAULT PRIVILEGES
CREATE PUBLICATION powersync FOR TABLE <synced tables>;  -- name MUST be "powersync"
```

- Postgres >= 11 required. One replication slot per instance (+1 transiently while a new sync config is processing): leave `max_replication_slots`/`max_wal_senders` at defaults (10) or higher; do not set them to 1.
- Use `sslmode: disable` only on the private compose network; production guide should keep Postgres off public interfaces.
- Monitor for abandoned replication slots (WAL retention can fill the disk if PowerSync is down for a long time); include in the ops/backup guide. (LOW-MEDIUM: standard Postgres behavior, not PowerSync-specific text.)

**Bucket storage:** Postgres (Beta) in a separate `powersync_storage` database, as decided above. MongoDB is the longer-proven, officially primary storage and the docs' production architecture assumes a 3-node Mongo replica set; for a single-VM research kit with daily-backed-up Postgres, Postgres storage is the better operational trade. Bucket storage is re-derivable from the source DB, so loss means a re-sync, not data loss.

**`service.yaml` skeleton (HIGH for shape; env substitution only works for `PS_`-prefixed vars):**

```yaml
replication:
  connections:
    - type: postgresql
      uri: !env PS_DATA_SOURCE_URI          # postgresql://powersync_role:...@postgres:5432/openwellness
      sslmode: disable
storage:
  type: postgresql
  uri: !env PS_STORAGE_SOURCE_URI           # postgresql://ps_storage:...@postgres:5432/powersync_storage
  sslmode: disable
port: !env PS_PORT                          # 8080
sync_config:
  path: sync-config.yaml
client_auth:
  jwks_uri: !env PS_JWKS_URL                # http://api:8000/.well-known/powersync-jwks.json
  audience: ["powersync"]
healthcheck:
  probes: { use_http: true }
api:
  tokens: [ !env PS_ADMIN_API_TOKEN ]       # local admin API auth; never leave default
```

Image command `["start","-r","unified"]`, `POWERSYNC_CONFIG_PATH=/config/service.yaml`, `NODE_OPTIONS=--max-old-space-size=<~80% of container memory>`. Migrations run automatically on start by default (fine for single-VM; use `migrate up` job only if scaling out).

**Auth: do NOT reuse the existing API access token.**

PowerSync requires a `kid` JWT header, `aud` matching `client_auth.audience`, `sub`, and `iat`+`exp` (max 24h; recommended <= 60 min; docs contain a conflicting "older than 60 minutes not accepted" sentence, so mint <= 15 min, matching the existing `access_ttl_seconds=900`). The existing tokens are HS256 with no `kid`, `aud=openwellness-api`, and the signing secret grants API admin. Pointing PowerSync at that secret would hand a second service the key that can forge admin/coach tokens, and would accept every API access token as a sync credential.

Instead: add a small `PowerSyncTokenService` (in the API's auth module) and an authenticated endpoint (e.g. `POST /v1/auth:powersyncToken`, outside the OTP flow, requires a valid API access token) that mints:

```
header: {alg: EdDSA|RS256, kid: <key id>}
claims: {sub: <user id>, aud: "powersync", iat, exp (<=15 min), participant: <participant id>, roles: [...]}
```

- **Recommended signing:** asymmetric (Ed25519/EdDSA or RS256), because the PowerSync docs say shared HS256 secrets are for dev/testing. The API publishes the public key as JWKS (`/.well-known/powersync-jwks.json`, unauthenticated, outside `/v1`), PowerSync reads it via `client_auth.jwks_uri` and refreshes every few minutes (rotation = publish new key, wait ~5 min, sign with it, retire old). The bootstrap/seed command generates the keypair if absent. (MEDIUM: design is straightforward but JWKS-over-compose-network and key-rotation behavior should be proven in the first PowerSync spike.)
- **Acceptable v1 shortcut / dev default:** HS256 with a *dedicated* secret (`API_POWERSYNC_JWT_SECRET`, distinct from `API_AUTH_JWT_SECRET`), configured as an inline `oct` JWK in `client_auth.jwks.keys` (`kty: oct`, `alg: HS256`, `kid`, `k: <base64url secret>`). The doc's `oct` shape is "standard JWK" and should be spike-verified; secret must be base64url-encoded in config.
- Mobile `fetchCredentials()` calls this endpoint with the existing Ktor bearer client and returns `PowerSyncCredentials(endpoint = <powersync URL>, token = ...)`; the SDK caches and re-calls near expiry.

**Sync Streams for participant scoping (HIGH for syntax, per `docs.powersync.com/sync/streams/queries`):**

```yaml
config:
  edition: 3
streams:
  participant_data:
    auto_subscribe: true
    queries:
      - SELECT * FROM weights  WHERE owner = auth.parameter('participant')
      - SELECT * FROM goals    WHERE owner = auth.parameter('participant')
      - SELECT * FROM fitbit_records WHERE owner = auth.parameter('participant')
      # ... one per synced table; all queries in a stream must share the same parameter inputs
```

- `auth.user_id()` = JWT `sub`; extra claims (our `participant`) are read via `auth.parameter('name')` (`auth.parameters()` for the whole object).
- Joins/subqueries are supported (`IN (SELECT ...)`, single-table-select `INNER JOIN`, CTEs via `with:`) for tables that reach the participant through a parent (e.g. study-scoped read-only data). Keep it to a few multi-query streams: each distinct stream/parameter combination creates buckets per user, and there are bucket-count limits (see `sync/streams/bucket-count` before adding many streams).
- Never accept `subscription.parameter(...)` for tenancy without an ownership check; the participant id must come from the signed token.
- Sync Streams are read-path only. Writes go through the API (below), so there is no client-trusted write path to PowerSync.

**Network/exposure:** Mobile clients talk to the PowerSync service directly (HTTP streaming), not through the API; the deployment guide needs a TLS-terminated public endpoint for it (docs recommend a dedicated subdomain), while Postgres, Redis, Mailpit UI stay on the private compose network. PowerSync's own dashboard is not available for self-hosted instances.

### 3. PowerSync Kotlin Multiplatform SDK

- **Artifacts:** `com.powersync:core` (+ `com.powersync:compose` for `rememberPowerSyncDatabase`; optional, since the app uses Koin, prefer constructing the `PowerSyncDatabase` as a Koin `single` and skipping the Compose helper). Targets: Android, iOS (`iosArm64`, `iosSimulatorArm64`; **`x86_64` Apple targets removed in 1.13.0**, which matches this repo), JVM, macOS; Web experimental (ignore).
- **Version choice:**
  - Latest: **1.15.2** (2026-09-28), built with Kotlin 2.4.20, Ktor 3.5.2, Gradle 9.7.x.
  - **1.14.1** (2026-07-29): Kotlin **2.3.21**, Compose MP 1.11.1, Ktor 3.5.0, coroutines 1.11.0, serialization 1.11.0 — matches this repo's Kotlin exactly. **Start here.**
  - 1.15.0 had an R8/release-build bug ("no such table: CRUD", fixed in 1.15.1) and 1.15.2 fixes "CRUD uploads not being retried on failure" (commit dated 2026-09-15; the first affected version was not determined). Since upload retry is the heart of this project's offline-write story, plan a toolchain bump (Kotlin 2.4.x, Compose MP 1.11.1+/1.12, Gradle 9.7) and move to >= 1.15.2 once the mobile phase is stable, and write a test that forces an upload failure and asserts retry on whichever version ships.
  - Transitive upgrades: PowerSync pulls coroutines 1.11.0 / serialization 1.11.0 / Ktor 3.5.x; this repo pins 1.10.2 / 1.10.0 / 3.5.0. Gradle will resolve to the higher versions; bump the version catalog to match to keep a single version of each.
- **Local DB:** PowerSync owns the SQLite database (bundled SQLite 3.5x on Native; PowerSync core extension linked statically on Apple targets since 1.12.0). `PowerSyncDatabase(factory = DatabaseDriverFactory(context | none), schema, dbFilename = "openwellness.db")`. Schema is declared client-side in Kotlin (`Schema(Table(...))`) and must mirror the synced Postgres columns; the implicit `id` column is added by PowerSync. UI reads via `db.watch(sql)` returning `Flow`, which fits the existing coroutines/Compose/Koin stack. Expect to write the table-per-entity `Table` definitions (~participant-scoped subset of the 50 entities).
- **Upload queue -> existing API:** subclass `PowerSyncBackendConnector`:
  - `fetchCredentials()`: call the PowerSync-token endpoint (above).
  - `uploadData(database)`: loop `database.getNextCrudTransaction()`; for each `CrudEntry` (`op` = PUT/PATCH/DELETE, `table`, `id`, `opData`) call the matching `/v1` AIP REST call with the app's authenticated Ktor client (PUT->create/replace, PATCH->update, DELETE->delete), then `transaction.complete()`. API must apply writes synchronously before responding 2xx.
  - Error policy (official guidance): 5xx/network = throw (SDK retries); validation/conflict 4xx = do not throw forever, or the queue blocks permanently. Return/log and `complete()` (or record in a synced error table) for non-retryable errors. Decide an explicit rule for 401 (refresh via Ktor Auth, then retry) vs 403/422 (drop + surface).
  - Naming mismatch to design for: local/Postgres columns are snake_case while the existing REST/Couchbase documents are camelCase (`fitbitDate`, `createdAt`). Either map in the connector or add a thin batch endpoint; decide in the architecture phase (the `/v1` contract itself must not change).
- **Lifecycle:** `database.connect(connector)` after login; `database.disconnectAndClear()` (clears local data by default) on logout — mandatory for a health-data app on shared/lost devices. Sync Streams client API: `database.syncStream(name, params).subscribe()` when manual subscriptions are needed (not needed with `auto_subscribe`).
- **Dev networking:** Android emulator reaches host via `10.0.2.2`; iOS simulator via `localhost`; real devices need the machine LAN IP or a tunnel. Cleartext HTTP is blocked by Android network security policy / iOS ATS unless explicitly allowed for dev builds. Both API URL and PowerSync URL must be configurable (the PowerSync endpoint is returned in the credentials response, so the server controls it).

### 4. Dev SMTP catcher

**Mailpit** (`axllent/mailpit:v1.32`), compose service:

```yaml
mailpit:
  image: axllent/mailpit:v1.32
  restart: unless-stopped
  ports: ["127.0.0.1:8025:8025"]      # UI + REST API; SMTP stays internal (mailpit:1025)
  environment:
    MP_MAX_MESSAGES: "500"
    MP_DATABASE: /data/mailpit.db
  volumes: ["mailpit_data:/data"]
```

- The existing `SmtpEmailSender` unconditionally runs `starttls()` when `SMTP_USE_TLS=true` (the default). Mailpit's SMTP is plaintext/unauthenticated unless given a cert, so the dev profile must set `SMTP_HOST=mailpit SMTP_PORT=1025 SMTP_USE_TLS=false` (no username/password). Do not configure Mailpit TLS just to satisfy STARTTLS; flip the flag instead. Put these as the dev defaults in `.env.example` and make production docs require `SMTP_USE_TLS=true` with real credentials.
- If someone sets SMTP credentials in dev, add `MP_SMTP_AUTH_ACCEPT_ANY=1` and `MP_SMTP_AUTH_ALLOW_INSECURE=1` (documented testing-only flags).

### 5. Postgres container / test tooling

- `testcontainers` 4.15.0 `PostgresContainer("postgres:18", driver="psycopg")` -> `postgresql+psycopg://user:pass@host:port/test`. Requires Docker; gate with an `integration` marker/skip-if-no-Docker.
- `testcontainers` also ships a `mailpit` module (extra `mailpit`) if the OTP e2e test should run against a real SMTP sink; optional.
- Use the same `postgres:18` image in tests and compose so behavior (including `wal_level=logical` runs) matches; to test the publication migration, start the test container with `.with_command("postgres -c wal_level=logical")`.
- Reuse the existing fakes (in-memory) for application-layer tests; add a *contract test suite* parameterized over repository implementations (fake vs Postgres) so adapters are provably port-equivalent.

## Installation

```bash
# Backend (uv workspace). In backend/core/pyproject.toml:
#   dependencies: "sqlalchemy>=2.1.6,<2.2", "psycopg[binary]>=3.3.6,<3.4", "alembic>=1.20.1,<1.21"
#   optional-dependencies.legacy: couchbase, pymongo, requests   (keep existing pins, incl. pymongo<4.14)
#   dev / integration extra: "testcontainers>=4.15,<5"
uv add --package openwellness-core "sqlalchemy>=2.1.6,<2.2" "psycopg[binary]>=3.3.6,<3.4" "alembic>=1.20.1,<1.21"
uv add --package openwellness-core --optional integration "testcontainers>=4.15,<5"

# Mobile: frontend/mobile/gradle/libs.versions.toml
#   powersync = "1.14.1"
#   powersync-core    = { module = "com.powersync:core",    version.ref = "powersync" }
#   powersync-compose = { module = "com.powersync:compose", version.ref = "powersync" }   # optional
#   (also align kotlinx-coroutines 1.11.0, kotlinx-serialization 1.11.0, ktor 3.5.0 -> as resolved)
# commonMain.dependencies { implementation(libs.powersync.core) }
```

```yaml
# docker-compose.yml additions (sketch)
postgres:
  image: postgres:18
  command: ["postgres", "-c", "wal_level=logical"]
  volumes: [pg_data:/var/lib/postgresql, ./docker/postgres/init:/docker-entrypoint-initdb.d:ro]
  healthcheck: { test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"], interval: 5s, retries: 10 }
migrate:
  build: { context: ./backend, target: api }
  command: ["alembic", "-c", "core/alembic.ini", "upgrade", "head"]
  depends_on: { postgres: { condition: service_healthy } }
powersync:
  image: journeyapps/powersync-service:1.27.2
  command: ["start", "-r", "unified"]
  environment: { POWERSYNC_CONFIG_PATH: /config/service.yaml, PS_DATA_SOURCE_URI: ..., PS_STORAGE_SOURCE_URI: ..., PS_JWKS_URL: http://api:8000/.well-known/powersync-jwks.json, PS_PORT: 8080 }
  volumes: [./docker/powersync:/config:ro]
  depends_on: { postgres: { condition: service_healthy }, migrate: { condition: service_completed_successfully }, api: { condition: service_started } }
mailpit:
  image: axllent/mailpit:v1.32
```

(`powersync` depends on `migrate` because the `powersync` publication and synced tables must exist before replication starts; Celery `beat` is a separate service from `worker`.)

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| SQLAlchemy Core (sync) + psycopg3 | SQLAlchemy ORM (imperative mapping) | Only if you later want relationship loading and are willing to let SA instrument the domain dataclasses. Not worth it with ports already returning dataclasses. |
| SQLAlchemy Core | psycopg3 + hand-written SQL / `psycopg.sql` | A very small schema. At ~50 tables + dynamic `filter=` it loses Alembic autogenerate and gets verbose. |
| Sync engine | Async SQLAlchemy / asyncpg | If the ports and handlers are ever moved to `async def`. Out of scope (wire contract and ports stay). |
| Alembic | Raw SQL migration files / Atlas / dbmate | If you want migrations independent of Python. Loses autogenerate and the in-repo `MetaData` as schema source of truth. |
| Postgres bucket storage (Beta), same server | MongoDB replica-set bucket storage | If the spike finds Postgres storage problems, or an adopting lab already runs Mongo; it is the longer-proven path. Adds a `mongo` container + replica set init to the kit. |
| Postgres bucket storage on same server | Second `postgres:18` container for storage | If WAL/IO contention or backup coupling matters; identical to the official demo topology. |
| Sync Streams (edition 3) | Sync Rules | Never for new work (deprecated). |
| Dedicated PowerSync token (asymmetric, JWKS) | Dedicated HS256 secret as inline `oct` JWK | Fastest v1; acceptable on a single trusted VM and for dev. Docs call HS256 dev/testing only. |
| Mailpit | MailHog / MailDev / smtp4dev | MailHog is unmaintained; others work but Mailpit's API + active releases win. |
| PowerSync Open Edition | ElectricSQL, Couchbase Lite + Sync Gateway (status quo), custom delta sync | Project constraint says PowerSync stands unless a hard blocker appears; research found none. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `journeyapps/powersync-service:latest` | Unpinned image makes the "one-command, reproducible" kit non-reproducible; sync-config features are version-gated | Pin `1.27.2` (bump deliberately) |
| Reusing the API access JWT (or the API signing secret) for PowerSync | PowerSync would hold a key able to forge admin/coach tokens; tokens lack `kid`; any API token becomes a sync credential | Separate `PowerSyncTokenService` with its own key and `aud=powersync` |
| `CREATE PUBLICATION powersync FOR ALL TABLES` in the shipped kit | Replicates every table (auth/refresh/OTP-adjacent) into bucket storage; extra memory and lag | Explicit table list maintained in Alembic migrations |
| Sync Rules (`sync_rules:` / `bucket_definitions`) | Deprecated being phased out | Sync Streams, `config: edition: 3` |
| Direct client writes to Postgres via PowerSync (e.g. Supabase connector) | Violates "server stays the authority for validation and auth" | `uploadData` -> existing `/v1` API |
| `asyncpg` / async SQLAlchemy | Mismatch with sync ports, sync handlers, Celery | psycopg3 sync |
| `psycopg2` | Legacy; SQLAlchemy 2.1 default is psycopg3; testcontainers default is `psycopg2`, so override | `psycopg[binary]` 3.3 |
| SQLAlchemy ORM `declarative` models as the domain | Leaks persistence into the Clean Architecture domain | Core `Table`s + mapper in the adapter |
| MailHog | Unmaintained | Mailpit |
| `DATABASE_URL` auto-`create_all()` at startup | Skips versioning; breaks "reproducible on fresh DB" and publication management | Alembic `upgrade head` in a one-shot `migrate` service |
| PowerSync Kotlin 1.15.0 | R8 release-build upload bug (fixed 1.15.1) | 1.14.1 now, >= 1.15.2 later |
| Letting PowerSync/Postgres ports bind `0.0.0.0` on the VM | Exposes DB/replication | Bind to `127.0.0.1` or keep internal; only the reverse proxy is public |

## Stack Patterns by Variant

**If a contributor's laptop dev stack (default `docker compose up`):**
- HS256 dev secret via `oct` JWK, `sslmode: disable`, Mailpit, Postgres storage on same server, `pg` exposed on 127.0.0.1 only.
- Because the goal is a one-command start with zero key management; the `.env.example` generator fills secrets.

**If single-VM production:**
- Asymmetric PowerSync token + JWKS, TLS-terminating proxy (Caddy/nginx) in front of api, dashboard static files, and PowerSync (own subdomain), real SMTP with `SMTP_USE_TLS=true`, Mailpit profile off (`profiles: ["dev"]`), daily `pg_dump` (+ WAL archiving optional) of both `openwellness` and `powersync_storage` (storage is rebuildable, so backing it up is optional), monitored replication slot.
- Because the docs recommend asymmetric keys outside dev and Beta storage should be backed by a tested restore path.

**If an adopting lab already runs MongoDB or needs HA sync:**
- Switch `storage.type` to `mongodb` (replica set) and split `start -r api` / `start -r sync` containers.
- Because that is PowerSync's documented production topology; out of scope for the v1 kit.

**If the legacy flag (`couchbase`) is selected:**
- Postgres, PowerSync, and Mailpit services are simply not started (compose profiles); offline-first sync is a Postgres-backend-only feature.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| SQLAlchemy 2.1.6 | Python >= 3.11 (project 3.12 OK); Alembic 1.20.1 (`SQLAlchemy>=2.0`); psycopg 3.3.6 | 2.1 makes psycopg3 the default `postgresql://` driver; still specify `postgresql+psycopg://` explicitly. `greenlet` no longer auto-installed (irrelevant for sync). |
| psycopg 3.3.6 | Python >= 3.10, Postgres 18 | `[binary]` wheels; no libpq needed in slim image. |
| powersync-kotlin **1.14.1** | Kotlin 2.3.21, Compose MP 1.11.1, Ktor 3.5.0, coroutines/serialization 1.11.0, AGP/Gradle per repo | Built against exactly the repo's Kotlin. Repo currently pins coroutines 1.10.2/serialization 1.10.0 — bump to 1.11.0. Repo Gradle is 9.1.0; 1.14.1's own build used a newer Gradle but consumers are not bound to it (verify in first build). |
| powersync-kotlin **1.15.2** | Kotlin 2.4.20 (1.15.0 used 2.4.10), Ktor 3.5.2, Gradle 9.7.x, Compose MP 1.12.0 in its sample | Requires Kotlin 2.4 toolchain bump of the whole mobile build. Reading a 2.4 klib from 2.3.21 is a gamble (Kotlin guarantees only limited forward compat); do the bump deliberately, not by accident. |
| PowerSync Service 1.27.2 | Sync Streams (needs >= 1.20), Postgres storage (>= 1.3.8), Postgres source >= 11, storage-on-same-server Postgres > 14 | Kotlin SDK >= 1.7.0 supports Sync Streams (Rust sync client default from 1.9.0; legacy Kotlin client removed in 1.12.0). |
| PowerSync JWT | `kid` header, `aud` in `client_auth.audience`, `sub`, `iat`/`exp` | Algorithms: RS256/384/512, EdDSA (Ed25519/Ed448), ES256/384/512, HS256/384/512. |
| Mailpit v1.32 | existing `smtplib` sender | Requires `SMTP_USE_TLS=false` unless Mailpit given a cert. |
| testcontainers 4.15 | Python >= 3.10, Docker; PostgresContainer `driver="psycopg"` | Default driver is psycopg2 — override. |
| Postgres 18 image | volume mounted at `/var/lib/postgresql` | Changed from `/var/lib/postgresql/data` in earlier majors; wrong mount path loses data on recreate. |

## Open Items to Prove in Early Spikes (not blockers)

1. PowerSync Postgres storage on the *same* server as the source (documented supported for PG > 14; Beta). Fallback: second container.
2. HS256 `oct` JWK exact YAML shape and `jwks_uri` over plain HTTP inside compose (demo uses HTTP, so likely fine).
3. Alembic 1.20.1 autogenerate + `op.execute` publication DDL against SQLAlchemy 2.1.6.
4. PowerSync Kotlin SDK 1.14.1 builds clean under the repo's Gradle 9.1.0 / AGP 9.0.1 and runs on both Android and iOS simulator; determine whether the "uploads not retried" bug affects 1.14.1.
5. Bucket-count limits vs. the number of participant-scoped tables (use one multi-query stream).
6. Replica identity: default (primary key) is sufficient for PowerSync replication of tables with PKs; confirm no table lacks a PK. (Doc page did not mention REPLICA IDENTITY.)

## Sources

- docs.powersync.com `configuration/powersync-service/self-hosted-instances.md` — service.yaml structure, storage types, client_auth, `!env` substitution, healthchecks (HIGH, official)
- docs.powersync.com `configuration/source-db/setup.md` — Postgres wal_level, role, publication name, grants, version >= 11 (HIGH, official)
- docs.powersync.com `configuration/auth/custom.md` — JWT requirements, algorithms, kid/aud/exp, HS256 secret setup (HIGH, official; one internal inconsistency about 60 min vs 24 h noted)
- docs.powersync.com `sync/streams/queries.md`, `sync/streams/overview.md`, `sync/streams/migration` — Sync Streams syntax, edition 3, Sync Rules deprecated, min service 1.20 / Kotlin SDK 1.7 (HIGH, official)
- docs.powersync.com `sync/types.md` — Postgres->SQLite type mapping (HIGH, official)
- docs.powersync.com `handling-writes/writing-client-changes.md` — upload queue, error handling guidance (HIGH, official)
- docs.powersync.com `client-sdks/reference/kotlin.md` — SDK install, targets, connector API, Apple static linking (HIGH, official)
- docs.powersync.com `maintenance-ops/self-hosting/deployment-architecture.md` and `securing-your-deployment.md` — topology and sizing (MEDIUM; Mongo-centric, security page is WIP)
- releases.powersync.com announcement `ann_AUNZWHlVzOeU2` — Postgres bucket storage is Beta, parity with Mongo (HIGH, official)
- github.com/powersync-ja/powersync-kotlin — CHANGELOG (1.12 -> 1.15.2), `gradle/libs.versions.toml` at tags v1.13.0, v1.14.1, v1.15.0, v1.15.2, issue #377 (HIGH)
- Maven Central `com.powersync` (`core`, `compose`) metadata — latest 1.15.2, 1.14.1 present (HIGH)
- Docker Hub `journeyapps/powersync-service` tags — 1.27.2 latest as of 2026-10-24 (HIGH)
- github.com/powersync-ja/self-host-demo (`demos/nodejs-postgres-bucket-storage`, `services/*.yaml`) — reference compose, `postgres:18`, `wal_level=logical`, `service.yaml` (HIGH)
- PyPI JSON: SQLAlchemy 2.1.6, Alembic 1.20.1, psycopg 3.3.6, psycopg-pool 3.3.3, testcontainers 4.15.0, PyJWT 2.15.1 (HIGH)
- docs.sqlalchemy.org/en/21 `changelog/migration_21` — psycopg3 default, Python 3.11 floor, behavior changes (HIGH, first ~100k of 146k chars read)
- mailpit.axllent.org docs `configuration/smtp` + GitHub release v1.32.0 / Docker Hub tags (HIGH)
- testcontainers-python docs `modules/postgres` — constructor, `driver` default psycopg2 (HIGH)
- endoflife.date PostgreSQL — 18.6 latest, EOL 2030-11 (HIGH)
- Local repo inspection: `auth/token_service.py` (HS256, no kid, aud `openwellness-api`, 900s TTL), `auth/email_sender.py` (unconditional STARTTLS when `use_tls`), sync `def` handlers, dataclass entities with `str(uuid4())` ids and float epoch timestamps, `frontend/mobile/gradle/libs.versions.toml` (HIGH)

---
*Stack research for: Postgres + PowerSync + self-host kit on OpenWellness*
*Researched: 2026-10-29*
