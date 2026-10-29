# Feature Research

**Domain:** Self-hostable, open-source research-study platform (Python API + React dashboard + KMP mobile) moving to Postgres + PowerSync, with route auth enforcement and a self-host kit
**Researched:** 2026-10-29
**Confidence:** MEDIUM overall (HIGH for PowerSync mechanics and peer packaging patterns, which come from official docs fetched this session; MEDIUM for research-platform peers and for judgment calls about what labs expect; LOW items are flagged inline)

Scope note: the existing system is mapped in `.planning/codebase/` and is not re-researched here. This file covers only the four target areas: (a) self-host kit, (b) offline-first sync, (c) auth enforcement, (d) selectable datastore backend. Complexity is relative to this codebase (Clean Architecture, ~41 ports, ~50 entities, ~260 routes).

## Feature Landscape

### (a) Self-Host Kit

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `git clone` + `cp .env.example .env` + `docker compose up -d` brings up a working stack | Immich, Plausible CE, Supabase all lead with exactly this; it is the unit of "self-hostable" | MEDIUM | Services: api, scheduler worker, scheduler beat, redis, postgres, powersync, dashboard, mailpit. Beat is currently missing from compose (CONCERNS: scheduler has no beat). |
| Healthchecks + `depends_on: condition: service_healthy` ordering | Supabase tells users to wait for `docker compose ps` to show healthy; without it first boot races (api before postgres, powersync before replication ready) | LOW | Postgres `pg_isready`, redis ping, api `/healthz`, powersync healthcheck probes (configurable via `healthcheck.probes`). Scheduler currently has no healthcheck (CONCERNS). |
| `.env.example` that lists EVERY required variable, grouped, with generation commands inline | Plausible (`openssl rand -base64 48`), Supabase (`generate-keys.sh`), Cal.com (`openssl rand -base64 32`) all do this. Current gap: `API_AUTH_JWT_SECRET` and `API_AUTH_CODE_PEPPER` are missing and the API refuses to boot | LOW | Placeholders must be obviously invalid (`CHANGE_ME`) so the boot guard rejects them. |
| Settings actually load from `.env` under compose AND when running services directly | The README audit found `.env` is never loaded (no `env_file`). This is a first-run blocker, not polish | LOW | Pydantic `env_file` in shared core settings plus compose `env_file:`. Consolidating settings into `core` (already in Active) is the natural home. |
| Fail-fast boot guard for placeholder/default/short secrets (extend to Postgres password, PowerSync keys) | Supabase: "never start with these defaults". CONCERNS flags Couchbase default `password` and Mongo unauthenticated URL | LOW | Existing 32-char guard in `main.py` extended; apply to scheduler too. |
| First-admin bootstrap command (idempotent) so a fresh instance is loggable-into | Plausible: first visitor registers. Cal.com and Immich docs leave this under-documented, which is a known user complaint pattern. Here login is OTP-only, so an admin row MUST exist before anyone can log in | MEDIUM | `python -m ... bootstrap --admin-email x` (CLI) plus optional env-driven `BOOTSTRAP_ADMIN_EMAIL` on first start. Must be idempotent and must not create a default-credential admin. |
| Optional demo seed (demo coach, study, participant) | Needed to exercise synced data and the mobile app without hand-crafting rows | LOW | Separate flag from admin bootstrap; refuse/skip in production profile. |
| Dev mail catcher so OTP emails are visible locally | OTP-only login makes this mandatory for evaluation: without SMTP nobody can log in | LOW | Mailpit (single binary/Docker image, SMTP + web UI + REST API usable in tests). Use it over MailHog. Web UI port exposed on localhost only. |
| Database migrations run automatically and reproducibly on a fresh DB | Cal.com/Plausible/Immich all migrate on start or document a one-liner; Active list requires "reproducible on a fresh database" | MEDIUM | One-shot `migrate` service (or entrypoint step) that api/scheduler wait for. |
| Pinned image tags/versions, not `latest` | Immich (`IMMICH_VERSION`), Plausible (git tag clone), Supabase (versioned snapshots) | LOW | `OPENWELLNESS_VERSION` env var; document how to choose. |
| Persistent named volumes for Postgres and Redis (AOF) | Redis currently has no persistence; a restart drops OTP records and queued tasks (CONCERNS) | LOW | Document what is and is not safe to lose (OTP/rate-limit = ephemeral; Postgres = precious). |
| One configuration reference table covering every variable (name, required?, default, example, which service) | Explicit Active requirement; Supabase and Immich ship env docs | MEDIUM | Generate from the settings classes to prevent drift (see Differentiators). |
| Single-VM production deployment guide: TLS/reverse proxy, real SMTP, secrets, CORS, backups, upgrades | Mattermost (nginx + TLS as production prerequisite), Plausible (80/443 auto-TLS), Supabase (HTTPS reverse proxy, SMTP via SES) | MEDIUM | Gated on auth enforcement landing first (PROJECT.md constraint). |
| Reverse proxy + TLS recipe that works copy-paste | Plausible defers to a wiki and Mattermost's docs conflict on TLS; both are known friction | LOW | Recommend Caddy (automatic Let's Encrypt, ~10-line Caddyfile) as the documented default; note nginx as alternative. Also configure uvicorn trusted `--forwarded-allow-ips` (CONCERNS: X-Forwarded-For rate-limit bypass). |
| Backup and restore procedure that has been actually tested | REDCap sites run daily DB dumps off-site as standard practice; Supabase and Immich install pages are silent on backup, and that silence is a recognised gap | MEDIUM | `pg_dump`-based script + cron example + a documented restore drill. PowerSync bucket storage is rebuildable from Postgres, so it does not need backup (MEDIUM confidence; verify during phase research). |
| Upgrade procedure: backup, bump version, pull, migrate, restart, rollback notes | Mattermost's guide opens with "ensure complete backup"; Immich has a dedicated Upgrading page | LOW | Include the PowerSync-specific caution: DDL is not replicated, so schema migrations that rename/drop need coordinated sync-config changes. |
| README quick start verified end-to-end on a fresh clone | Explicit Active requirement; current README has known inaccuracies | MEDIUM | See CI-verified quickstart under Differentiators. |
| Dashboard production build/hosting doc (build-time `VITE_API_BASE_URL`, CORS match) | Explicit Active requirement; baked-at-build env is a classic self-host trap | LOW | Prefer serving static build from the same reverse proxy; state that API URL is compiled in. |
| Mobile dev build pointable at any server via documented config (incl. iOS URL) | Explicit Active requirement; no hardcoded localhost | MEDIUM | Single documented config surface (Gradle property / build config / plist) for API base URL and PowerSync URL. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `generate-secrets` helper script (writes `.env` with random secrets AND the PowerSync JWKS keypair) | Supabase ships `generate-keys.sh`; PowerSync's own self-host-demo ships a `key-generator/`. Removes the most error-prone first-run step for non-engineers (lab staff) | LOW | Emit asymmetric keypair for PowerSync JWT signing (see (b)); never emit HS256 for production. |
| `doctor`/preflight command (checks env completeness, secret strength, DB reachability, migrations current, SMTP test, CORS vs dashboard origin, PowerSync reachable, JWKS served) | None of the peers surface this well; turns a 30-line "it doesn't work" support thread into one command. PowerSync CLI offers similar validation, which sets a precedent | MEDIUM | Reuses the same settings classes as the boot guard. |
| CI job that runs the README quickstart literally on a clean runner (compose up, bootstrap, login via Mailpit API, hit an authed route, sync smoke) | Docs rot is the dominant failure of OSS self-host (the project's own audit proves it). Mailpit's REST API makes OTP login scriptable | MEDIUM | Also closes the "no CI at all" gap (CONCERNS). |
| Config reference generated from the pydantic settings classes | Single source of truth; reference cannot drift from code | LOW | Pairs with settings consolidation in `core`. |
| Backup/restore scripts exercised in CI (backup, wipe, restore, verify row counts) | An untested backup is not a backup; REDCap sites treat this as an operational SLA | MEDIUM | Defer if scope tight; the doc-only version is table stakes. |
| Prebuilt multi-arch images on GHCR for api/scheduler/dashboard | Immich/Plausible/Mattermost users pull, not build; speeds first run, enables pinned versions | MEDIUM | Needs release workflow (no CI exists yet). |
| Research-lab data-governance appendix (data inventory, what PII/PHI is stored, where, encryption-at-rest and TLS expectations, retention, audit-log availability, BAA/IRB talking points) | Target adopters are labs filing data-security plans; REDCap docs note BAA requirements for cloud PHI hosting. Almost no OSS research platform answers this up front | LOW | Documentation only; honest about what the software does NOT guarantee (HIPAA is not certified by a platform; MEDIUM confidence, domain judgment). |
| Small-footprint positioning: documented minimum VM size and expected load | Peers set a contrast: Beiwe's single-server AMI is for evaluation only (about 20 participants max per its old wiki); RADAR-base stack targets 16 GB / 4 CPU with Kafka; REDCap requires institutional IT and a license. A lean single-VM production path is a genuine advantage | LOW | Requires measuring, not guessing; add a sizing section after a load smoke test. |
| Compose profiles: `dev` (mailpit, exposed ports, seed) vs `prod` override (no mail catcher, no published DB ports, restart policies) | Prevents dev conveniences leaking into production (Supabase checklist spirit) | LOW | `compose.yaml` + `compose.prod.yaml` or profiles. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Web-based setup wizard / installer UI | Friendly for non-technical labs | A pre-auth setup endpoint is a takeover vector on an instance holding health data; extra surface to secure and test | CLI bootstrap + `doctor`; docs written for a lab sysadmin |
| Kubernetes/Helm chart, multi-node, managed-cloud guides | "Enterprise ready" | Explicitly out of scope; doubles docs and test matrix | Single-VM guide only; revisit post-v1 |
| Built-in TLS termination / ACME inside the API | Fewer moving parts | Reimplements a solved problem; Mattermost docs show the TLS-on-app-plus-proxy confusion | Caddy (or nginx) in front, trusted-proxy headers configured |
| Auto-update (Watchtower-style) | "Stay current" | Silent upgrades of a stack with migrations and non-replicated DDL can corrupt sync state; studies need controlled change windows | Documented manual upgrade with pinned versions and backup first |
| Default demo credentials / seeded admin password | "Instant login" | Classic exposed-instance vulnerability | Admin bootstrap by email via OTP; seed only in dev profile |
| Bundled mail server | "No SMTP setup" | Deliverability and blocklist problems; operational burden | Mailpit for dev, real SMTP (SES/Mailgun/institutional relay) for prod |
| Admin UI for editing server configuration | "No .env edits" | Secrets in DB, restart semantics, audit surface | `.env` + config reference + `doctor` |
| Bundled backup-to-cloud service | "One-click backups" | Credentials, cost, and compliance decisions belong to the lab/IRB | Script + cron + documented off-site copy guidance |
| ETL/migration from legacy Couchbase/Mongo | Existing deployments want it | Out of scope per PROJECT.md; high risk | Legacy flag keeps old deployments running |

### (b) Offline-First Mobile Sync (PowerSync)

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Self-hosted PowerSync service in the compose stack, wired to Postgres (logical replication) | Core of the milestone. PowerSync Service ships as a Docker image (`journeyapps/powersync-service`) configured by `service.yaml`; Postgres needs `wal_level=logical`, a dedicated replication role, and a publication literally named `powersync` | MEDIUM | Postgres container must start with logical replication on. Publication should list explicit synced tables, not `FOR ALL TABLES` (the service reads every change in the publication, and `FOR ALL TABLES` would pull in auth/session/audit tables). |
| Bucket storage choice that does not re-introduce Mongo | PowerSync supports MongoDB or Postgres bucket storage (Postgres 14+ can share the same server, or use a separate DB). The whole point is leaving Mongo | LOW | Recommend Postgres bucket storage in its own database/schema with a dedicated user. Confirm in stack research (MEDIUM confidence: PowerSync's own self-host-demo has a Postgres-storage variant). |
| API issues short-lived PowerSync JWTs; PowerSync verifies via the API's JWKS endpoint | PowerSync needs `sub`, `aud` (must match `client_auth.audience`), `kid`, `iat`, `exp`; `exp - iat` <= 24 h, docs recommend <= 60 min; asymmetric (RS/ES/EdDSA) recommended, HS256 dev-only. Mobile `fetchCredentials()` calls an authenticated API endpoint that mints the token | MEDIUM | Implies the API must start signing with an asymmetric key and expose a JWKS (or load static public keys into `service.yaml`). The existing 32-char HS secret JWTs for the app are a separate thing; do not reuse the symmetric secret for PowerSync. Rotation: publish new key, wait about 5 min, switch, retire old. |
| Sync config scoping each device to its participant (`sub`/participant claim -> rows) | The security boundary for offline data. PowerSync Sync Streams (successor to Sync Rules, which are legacy) filter on `auth.user_id()` or custom token parameters; the service builds one bucket per user | MEDIUM | Prefer Sync Streams for new work (legacy Sync Rules still work but get no new features; verify which the pinned service version supports). Client-supplied parameters must never gate access. |
| Every synced Postgres table has a single text primary key named `id` (UUID) | PowerSync requires it; composite and integer keys do not work offline | MEDIUM-HIGH | Directly constrains the Postgres schema design for ~50 entities. Existing AIP resource-name ids must map to UUID-like text ids; sequential ids are not creatable offline. Decide at schema time, not later. |
| Local SQLite DB on device holding all participant-scoped data, readable offline | Explicit requirement | MEDIUM | Kotlin Multiplatform SDK targets Android and Apple (iOS); described as stable 1.x (feature-status page says GA; the Kotlin reference page text still says beta; MEDIUM confidence, verify at phase start). Define client schema once in Kotlin; PowerSync applies it as SQLite views, so no client-side migrations. Doc does not state Compose Multiplatform specifics; the SDK is UI-agnostic (LOW on any CMP-specific gotchas). |
| Offline writes go to the local DB and queue; `uploadData()` replays them through the existing `/v1` REST API | Explicit requirement ("server stays the authority"). PowerSync's upload queue records PUT/PATCH/DELETE per row; the connector maps each op to the matching API call and then calls `complete()` | HIGH | Biggest build item. Needs a generic op->route mapper over ~entity types, auth refresh handling, and batching. Rows are applied by the API (validation, owner binding), then replicate back down. |
| Correct upload error semantics: 5xx/network = retry; permanent 4xx must not wedge the queue | PowerSync docs: a 4xx without `complete()` retries forever and blocks the whole upload queue; recommended to return 2xx-equivalent handling and surface the error (response or an error table synced to the client) | MEDIUM | Decide per-error: validation reject => complete + record rejection locally; 401 => refresh token and retry; 5xx => retry. |
| Idempotent uploads keyed by client-generated UUID | Retried uploads must not duplicate rows (PowerSync docs do not discuss idempotency, so the API must provide it) | MEDIUM | PUT-as-upsert on the client id; owner-scoped create endpoints accept client-supplied ids. May need an API tweak against pure AIP "server assigns id" convention; keep wire contract stable by allowing an optional id. |
| Server-ingested wearable data (Fitbit/ActiGraph) replicates down automatically, read-only on device | Explicit requirement; works for free because PowerSync replicates Postgres WAL regardless of which process wrote the row | MEDIUM | Streams for those tables are download-only; `uploadData()` must reject/ignore writes to server-owned tables. Device must not be able to author wearable rows. |
| Bounded download scope for high-volume tables (time-window or on-demand subscription) | ActiGraph/Fitbit minute-level data can be very large; syncing a participant's entire history to a phone is a battery/storage/first-sync problem | MEDIUM | Sync Streams support on-demand subscriptions and parameters; use a rolling window by default (for example last N days) with on-demand history fetch. Sizing needs real data (LOW confidence on thresholds). |
| Soft-delete / purge semantics defined for sync | API has `:undelete`/`:purge` and soft deletes; a replicated "deleted" flag vs. row removal changes what devices see | MEDIUM | Stream queries should exclude soft-deleted rows (so devices drop them) and purge must remove rows; verify behavior on client. |
| Logout/account switch wipes the local DB (`disconnectAndClear`) | Shared/lost devices hold health data; mandatory privacy hygiene | LOW | Also clear on refresh-token revocation. |
| Visible sync status in app (connected, last synced, pending uploads) | Offline-first users need to trust that data is safe | LOW-MEDIUM | SDK exposes connection/status; minimal indicator suffices (no new study UI). |
| Postgres schema-change discipline for sync | PowerSync replicates DML only. Renames, drops, type changes and non-NULL defaults are not propagated; renames re-replicate the table and block replication | MEDIUM | Process rule plus migration review checklist; additive-only migrations as default. |
| Secure the PowerSync service itself (private network to Postgres, only the sync port exposed through proxy, admin API tokens set, telemetry reviewed) | Research data; Supabase checklist spirit. Service.yaml has a `telemetry` section and `api.tokens` | LOW | Put PowerSync behind the same reverse proxy with TLS; Postgres port never published in prod. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Server-reported rejection channel: rejected offline writes recorded in a synced "sync_errors" table | Gives users and coaches an honest account of what the server refused instead of silent data loss; PowerSync docs explicitly recommend this pattern | MEDIUM | Also valuable for debugging in the field. |
| Custom write checkpoints / read-your-writes guarantee | Without it, freshly uploaded rows can flicker (disappear then reappear) in the UI; matters for the participant experience | MEDIUM-HIGH | PowerSync has a custom write checkpoint option; adopt only if flicker shows in testing. |
| Encryption of local DB at rest (SQLCipher) | Phones hold PHI offline | MEDIUM | LOW confidence that the Kotlin SDK supports it cleanly; spike before promising. OS file-level encryption is the baseline. |
| Parity testing harness: write offline, reconnect, assert server row + sync back, with fake API | Offline bugs are the costliest to find in the field; existing "tests need no live infra" philosophy extends here | HIGH | Defer to a verification phase; at minimum a documented manual offline drill. |
| Per-stream subscription on demand (history, long-range wearable charts) | Keeps default footprint small while letting participants view history when online | MEDIUM | Builds on windowed streams above. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Device writes directly to Postgres (bypassing the API) | Simpler connector | Skips validation, owner binding, audit stamping; violates "server stays the authority" | `uploadData()` -> existing `/v1` API |
| Sync the whole database / `FOR ALL TABLES` publication | "Easy" | Leaks/overloads: auth sessions, other participants, admin data are replicated through the service; large volumes | Explicit table publication + per-participant streams |
| Dashboard/coach offline sync | Parity | Out of scope; coaches would need many participants' data on a device | Dashboard stays online REST |
| CRDT/automatic field-level merge engine | "No conflicts ever" | Overkill; participant data is mostly single-writer per row | Server-authoritative last-write-wins per row; reject invalid writes |
| Client-authored wearable/ingested records | Convenience | Breaks provenance of device data | Download-only streams for server-owned tables |
| HS256 shared secret for PowerSync in production | Quick start | PowerSync advises against it; secret on both sides, no clean rotation | Asymmetric JWKS |
| Long-lived PowerSync tokens | Fewer refreshes | Tokens cannot be revoked without rotating keys | <= 60 min tokens, refresh via API |
| Rebuilding the legacy offline model with custom sync code | Control | Re-creates what PowerSync provides; large bug surface | Use PowerSync; only hard blocker triggers reconsideration |

### (c) API Authentication and Authorization Enforcement

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deny-by-default: router-level dependency on `/v1` requiring a verified bearer token; explicit allow-list only for `/v1/auth:*` and `/healthz` | CONCERNS: 0 of ~260 routes authenticate today; health data is exposed. Deny-by-default (versus per-route opt-in) is what makes new routes safe | MEDIUM | Apply at the `v1` router include; the 36 modules using `get_principal` for stamping migrate to the strict dependency. |
| Owner binding: token `sub`/participant claim must equal `{user}` path segment on owner-scoped routes | Stops the horizontal-privilege attack (read/alter another user's weights by id). `check_parent` only prevents cross-parent confusion | MEDIUM | Central dependency, not per-handler code; 403 (or 404 to avoid enumeration; decide and document) on mismatch. |
| Role gates: admin routes and `GET /v1/users` need `admin`; coach capabilities need `coach`; participant default | `AccessClaims.roles` is parsed but never checked | MEDIUM | Define role vocabulary, where roles are stored/issued (token claim sourced from user record), and the exact route-to-role policy table. |
| Audit stamping from the verified principal only; drop trust in `X-Principal-Id` | CONCERNS: header lets anyone forge `updated_by` | LOW | Remove the header path entirely once bearer auth is mandatory. |
| `API_AUTH_ENFORCE_PRINCIPAL` default on (or remove the flag) | A permissive default makes the whole feature opt-in per environment | LOW | Keep an escape hatch only for tests, via test fixtures, not env. |
| Consistent 401 vs 403 semantics in the existing AIP-193 error format, with `WWW-Authenticate` on 401 | Wire contract stability: dashboard and mobile already parse these errors | LOW | Dashboard/mobile refresh flows must treat 401 -> refresh -> retry once. |
| Test that every registered route rejects anonymous calls (route-inventory test) | CONCERNS rates "no test asserts 401" as High priority; route inventories catch newly added unprotected routes | MEDIUM | Iterate `app.routes`; allow-list is the only exception set. Plus owner-mismatch and wrong-role tests per route class. |
| Trusted-proxy handling for client IP in rate limiting | CONCERNS: first `X-Forwarded-For` hop is trusted blindly | LOW | uvicorn `--proxy-headers --forwarded-allow-ips` and document the proxy chain in the deployment guide. |
| Existing clients keep working: dashboard and mobile send bearer tokens on all calls | Mobile app is currently auth-only; dashboard already gated | LOW-MEDIUM | Verify every dashboard call and every new mobile/PowerSync-connector call carries the token; refresh-on-401 behavior. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Route policy registry: each route declares its policy (public / authenticated / owner / coach / admin); CI fails on undeclared | Makes authorization reviewable in one table; auditors (IRB, security reviewers) can read it | MEDIUM | Can be a decorator/dependency factory emitting metadata used by the inventory test. |
| Coach-to-participant scoping (coach only reaches participants in their studies) | REDCap's analogue is per-project user rights and Data Access Groups; a bare "coach role" gate lets any coach read any participant's health data | HIGH | Depends on whether the data model already links coaches to studies/participants (not verified here). Flag as a requirements decision: ship role gate in v1 and document the limit, or include scoping. |
| Persistent audit log of admin and owner data changes (who, what, when, from verified principal) | CONCERNS lists "no audit log" as missing critical; research governance expects change traceability | MEDIUM | Append-only Postgres table written by a shared handler. Must NOT be in the PowerSync publication. |
| Admin user-management endpoints (invite coach, deactivate user, revoke sessions) | Without them the first admin cannot onboard coaches except through DB access | MEDIUM | Deactivation should revoke refresh sessions and stop PowerSync token issuance. |
| Postgres Row Level Security as defense in depth | Blocks data leaks from an app-layer bug | HIGH | PowerSync's replication role needs `BYPASSRLS`, and the API connection pooling complicates per-request settings; treat as optional hardening, never the primary control. |
| Sync-rule/API authorization parity test | Two authorization surfaces now exist (API routes and PowerSync streams); they must agree on who can see which rows | MEDIUM | A test that derives expectations from one policy table is ideal; at minimum a checklist. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| SSO (OIDC/SAML) / institutional login | Labs and IT ask for it; REDCap supports it | Large surface and per-institution variance; not needed to unlock v1 | Email-OTP stays; document as future |
| Custom role/permission editor, per-field ACLs, policy engines (OPA/ABAC) | "Flexible" | Premature; hard to test and audit | Fixed roles (participant, coach, admin) with a policy table |
| Password login / MFA stack | Habit | New credential store and reset flows; OTP already works | Keep OTP |
| Third-party API keys / OAuth app platform | Integrations | Out of scope for the platform milestone | Defer |
| Trusting client-supplied identity headers or claims for access (including PowerSync client parameters) | Convenience | Spoofable | Verified token claims only |
| "Permissive rollout" flag shipped on | Safe rollout | The current dead-code state is exactly this failure mode | Enforce by default, fix tests |

### (d) Selectable Datastore Backend (Postgres default, legacy behind flag)

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| One config switch (for example `DATASTORE_BACKEND=postgres|legacy`), default Postgres | Explicit requirement; selected at startup in the DI container | MEDIUM | Ports stay the only persistence surface; the container maps each port to the chosen adapter set. Mixed per-entity backends are not offered. |
| Only the chosen backend's settings are required | A Postgres user should not be forced to set Couchbase/Mongo variables, and vice versa; currently Couchbase has a default `password` | LOW | Conditional validation in shared settings (in `core`, consolidating the duplicated api/scheduler classes). |
| Postgres adapters for all ~41 ports, including refresh-session store and other auth persistence | Explicit requirement | HIGH | The bulk of the migration. Generic base repository mirroring the existing base classes keeps per-entity cost low. |
| Versioned, reproducible migrations (Alembic is the de facto choice for SQLAlchemy; confirm in STACK) | Cal.com (Prisma), Immich and Plausible all migrate automatically; CONCERNS shows the immutable-index pain of unmanaged schema | MEDIUM | Run via the one-shot migrate step; forward-only with documented rollback by restore. |
| Same behavior contract on every adapter (port contract tests run against Postgres, Mongo, Couchbase fakes/real) | Retaining legacy adapters is only safe if they keep passing the same behavioral suite; CONCERNS notes adapters currently lack real-DB tests | MEDIUM-HIGH | Parametrized contract suite; Postgres leg runs against a containerized Postgres (existing constraint), others against fakes. |
| Existing suites still run with no live infra (in-memory fakes) | Explicit constraint | LOW | New Postgres integration tests are marked and optional locally. |
| Clear startup error if a selected backend is unreachable or misconfigured (not a masked 404) | CONCERNS: Mongo repo swallows exceptions and returns None | LOW-MEDIUM | New adapters should let infrastructure errors propagate to the global handlers. |
| Docs: which features need which backend | PowerSync requires Postgres; selecting `legacy` therefore means no offline sync | LOW | Prominent compatibility note; legacy compose profile for Couchbase/Sync Gateway/Mongo, not part of the default stack. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Compose profile `legacy` that stands up Couchbase/SG/Mongo for existing deployments | Keeps existing deployments reproducible without cluttering default `docker compose up` | LOW | Docs only plus profile wiring. |
| Settings consolidated in `core` with typed per-backend sections | Removes drift between api and scheduler | LOW | Already an Active requirement. |
| Startup `doctor` check for backend consistency (migrations current for Postgres; indexes present for legacy) | Catches half-applied upgrades early | MEDIUM | Reuses the preflight command. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Dual-write / runtime hot-switch between stores | Zero-downtime migration | Consistency nightmares; ETL is explicitly out of scope | Choose backend at install time; new instances start fresh |
| Per-entity mixed backends | Incremental migration | Cross-store joins/consistency, untestable matrix | Whole-instance switch |
| Generic ORM/abstraction forcing Mongo/Couchbase through SQL semantics | Single code path | Defeats the ports/adapters design; leaks | Keep adapters behind ports |
| Removing the legacy adapters now | Smaller codebase | Breaks existing deployments | Keep behind flag; revisit later |
| ETL tooling from Couchbase/Mongo to Postgres | Existing users want it | Out of scope; high risk | Document "new instances start fresh" |

## Feature Dependencies

```
Auth enforcement (c: router-level bearer + owner binding + roles)
    └──gates──> Production deployment guide (a)           [PROJECT.md constraint]
    └──gates──> PowerSync token endpoint (b)               [token minted only for verified principal]
    └──required by──> Offline uploadData via API (b)       [uploads hit enforced routes]

Settings consolidated in core (d) ──> .env loading + .env.example + config reference (a)
Postgres schema + migrations (d)
    └──requires──> text UUID `id` PKs on every synced table (b)
    └──requires──> Postgres adapters for all ports (d)
    └──required by──> Self-host stack with postgres service (a)
    └──required by──> PowerSync logical replication + publication (b)

Asymmetric JWT signing + JWKS in API (c/b) ──> PowerSync client_auth (b) ──> fetchCredentials in mobile (b)
Bootstrap admin command (a) ──requires──> user store on Postgres (d) AND role model (c)
Mailpit (a) ──enables──> OTP login in dev, CI-verified quickstart (a), mobile dev builds (b)
Wearable ingestion (existing scheduler/API) ──writes──> Postgres ──replicates via──> PowerSync streams (b, download-only)
Sync streams (b) ──must agree with──> API authorization policy (c)
Audit log (c) ──excluded from──> PowerSync publication (b)
Mobile base-URL config (a) ──required by──> mobile pointed at self-hosted API + PowerSync (b)

legacy datastore flag (d) ──conflicts──> PowerSync/offline sync (b)  [sync needs Postgres]
Dual-write / hot switch ──conflicts──> "new instances start fresh" scope
```

### Dependency Notes

- **Auth before docs:** PROJECT.md forbids shipping production deployment docs before route enforcement. Enforcement also makes the PowerSync token endpoint safe to add. Ordering: (c) first or in parallel with (d), then (b), with (a)'s production guide last.
- **Schema drives sync:** The PowerSync `id` requirement means id strategy must be decided while designing the Postgres schema, otherwise a later retrofit touches every table, adapter, and the mobile schema.
- **Two authorization surfaces:** API enforcement does not protect data that PowerSync streams to a device; stream definitions are a second policy implementation. Keep one written policy table that both derive from.
- **Bootstrap needs both data and roles:** The first-admin command cannot be built until the user table exists on Postgres and the admin role semantics are defined.
- **Legacy flag vs sync:** Legacy datastore selection disables offline sync. Say so explicitly everywhere the flag is documented.
- **PowerSync Open Edition caveats:** The service is source-available under the Functional Source License (not an OSI license), and the product matrix lists self-hosted Open Edition as Beta (core described as stable). For an NIH-supported open-source project, record this in the license/NOTICE discussion and in the risk register (MEDIUM confidence; based on the vendor's release post).

## MVP Definition

### Launch With (v1)

- [ ] Deny-by-default bearer enforcement, owner binding, admin/coach role gates, header-spoof removal, enforce-on default, route-inventory 401 test (c) — security prerequisite for everything else
- [ ] Postgres adapters for all ports, versioned migrations, text-UUID `id` schema compatible with PowerSync, backend switch with Postgres default, legacy behind flag (d)
- [ ] Settings in `core`, `.env` loading, complete `.env.example`, boot guards (a)
- [ ] `docker compose up` full stack incl. scheduler beat, PowerSync, Mailpit, healthchecks, auto-migrate (a)
- [ ] First-admin bootstrap (idempotent) + optional demo seed (a)
- [ ] PowerSync: asymmetric JWT + JWKS, token endpoint, per-participant streams, replication-ready Postgres, mobile local DB, `uploadData()` through API with correct error semantics, download-only wearable tables, wipe-on-logout (b)
- [ ] Single-VM production guide: Caddy TLS, SMTP, secrets, CORS, backups (with tested restore), upgrades, trusted-proxy config (a)
- [ ] Config reference table; dashboard hosting doc; mobile server-URL config incl. iOS (a)
- [ ] README quickstart verified end to end (a)

### Add After Validation (v1.x)

- [ ] `generate-secrets` helper and `doctor` preflight — add once the variable set stabilizes
- [ ] CI-run quickstart and backup/restore drill — after a CI pipeline exists
- [ ] Audit log table and admin user-management endpoints — once the role model is settled
- [ ] Sync-rejection channel table, windowed/on-demand history streams — once real wearable volumes are measured
- [ ] Route policy registry and sync/API parity test
- [ ] Prebuilt GHCR images
- [ ] Research-lab data-governance appendix

### Future Consideration (v2+)

- [ ] Coach-to-participant scoping beyond role gates (unless the data model already supports it cheaply; requirements decision)
- [ ] Local DB encryption (SQLCipher) pending SDK spike
- [ ] Postgres RLS as defense in depth
- [ ] SSO/OIDC, Kubernetes/multi-node guides, mobile release builds and distribution

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Deny-by-default auth + owner binding + roles | HIGH | MEDIUM | P1 |
| Postgres adapters + migrations + backend switch | HIGH | HIGH | P1 |
| Settings consolidation, `.env` loading, `.env.example` | HIGH | LOW | P1 |
| Compose stack with healthchecks, Mailpit, beat, auto-migrate | HIGH | MEDIUM | P1 |
| First-admin bootstrap + seed | HIGH | MEDIUM | P1 |
| PowerSync service + JWKS auth + streams | HIGH | MEDIUM | P1 |
| Mobile local DB + `uploadData()` via API | HIGH | HIGH | P1 |
| Wearable download-only sync with bounded window | HIGH | MEDIUM | P1 |
| Production guide (TLS/backup/upgrade) | HIGH | MEDIUM | P1 |
| Config reference + dashboard/mobile config docs | HIGH | LOW-MEDIUM | P1 |
| Wipe-on-logout, sync status indicator | MEDIUM | LOW | P1 |
| `generate-secrets`, `doctor` | MEDIUM | LOW-MEDIUM | P2 |
| CI-verified quickstart, backup drill | HIGH | MEDIUM | P2 |
| Audit log, admin user management | MEDIUM-HIGH | MEDIUM | P2 |
| Sync rejection channel, custom write checkpoints | MEDIUM | MEDIUM | P2 |
| Route policy registry, authz parity test | MEDIUM | MEDIUM | P2 |
| GHCR prebuilt images | MEDIUM | MEDIUM | P2 |
| Data-governance appendix | MEDIUM | LOW | P2 |
| Coach-to-participant scoping | HIGH (if multi-coach) | HIGH | P2/P3 (decision) |
| Local DB encryption, RLS | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Immich / Plausible CE / Supabase / Cal.com | Mattermost / REDCap / Beiwe / RADAR-base | Our Approach |
|---------|--------------------------------------------|------------------------------------------|--------------|
| Install | Immich: download compose + `example.env`, `docker compose up -d`. Plausible: clone pinned tag, `.env`, compose up. Supabase: setup script or clone + `.env.example`, `run.sh start`. Cal.com: build-from-source or one-click hosts; Docker documented separately | Mattermost: separate docker repo, nginx optional third container. REDCap: PHP/MySQL, institutional IT, license required. Beiwe: single-server AMI for evaluation only, cluster for real use. RADAR-base: Kafka-based stack, 16 GB / 4 CPU baseline | Clone + `.env` + `docker compose up`; small stack on a single VM suitable for real studies |
| Secret generation | Plausible `openssl` one-liners; Supabase `generate-keys.sh` and a fixed key-length rule set; Cal.com `openssl rand` | Mostly manual | `.env.example` with inline commands (P1); `generate-secrets` helper (P2) |
| First admin | Plausible: first user registers in UI (open-registration risk). Immich/Cal.com: weak or absent in install docs | REDCap: admin created at install via config | CLI bootstrap, idempotent, OTP login; no pre-auth setup page |
| TLS / reverse proxy | Plausible auto-TLS via 80/443 (proxy docs deferred to wiki); Supabase says put an HTTPS proxy in front | Mattermost: nginx, TLS terminated at proxy | Caddy default recipe plus trusted-proxy settings |
| Backups | Supabase install docs silent; Immich install page points elsewhere; Plausible defers to wiki | REDCap institutions: daily DB dumps, off-site copies; Mattermost: back up DB + data dir before upgrading | Documented `pg_dump` flow with a tested restore; optional CI drill |
| Upgrades | Immich dedicated page + pinned version; Supabase `update.sh` three-way merge, monthly snapshots; Plausible pinned tags; Cal.com "upgrade DB before build" | Mattermost: backup first, version-specific notes; REDCap: backup DB+files, run upgrade script | Backup, bump pinned version, migrate, restart; note PowerSync DDL caveats |
| Email in dev | Supabase/Plausible need real SMTP or workarounds | n/a | Mailpit in dev profile |
| Offline-first mobile | Not applicable to these web apps | Beiwe/RADAR-base: passive collection apps that buffer and upload; REDCap mobile app caches data for offline entry | PowerSync-based bidirectional sync with server-authoritative uploads (LOW confidence on peer offline details; not verified in depth) |
| AuthZ | Roles (Mattermost), Data Access Groups / user rights (REDCap) | Per-project rights | Fixed roles + owner binding; scoping decision flagged |
| Config reference | Supabase/Immich ship env tables | Varies | One generated reference table |

## Sources

- PowerSync docs, fetched 2026-10-29: [self-hosting overview](https://docs.powersync.com/self-hosting/getting-started), [PowerSync Service setup](https://docs.powersync.com/self-hosting/installation/powersync-service-setup), [custom auth](https://docs.powersync.com/configuration/auth/custom), [Postgres source setup](https://docs.powersync.com/configuration/source-db/setup), [Sync Rules (legacy)](https://docs.powersync.com/usage/sync-rules), [Sync Streams overview](https://docs.powersync.com/sync/streams/overview), [writing client changes](https://docs.powersync.com/handling-writes/writing-client-changes), [client-side IDs](https://docs.powersync.com/sync/advanced/client-id), [implementing schema changes](https://docs.powersync.com/maintenance-ops/implementing-schema-changes), [Kotlin SDK reference](https://docs.powersync.com/client-sdks/reference/kotlin) (HIGH, official docs)
- [PowerSync self-host-demo repository](https://github.com/powersync-ja/self-host-demo) (HIGH for structure; Postgres-bucket-storage variant noted)
- [PowerSync Open Edition release post](https://powersync.com/blog/powersync-open-edition-release) and [Kotlin SDK 1.0.0 announcement](https://releases.powersync.com/announcements/powersync-kotlin-multiplatform-sdk-v1-0-0) (MEDIUM; license and maturity statements should be re-verified at phase start, and docs pages conflict on beta/GA for the Kotlin SDK)
- Peer self-host docs: [Immich Docker Compose install](https://docs.immich.app/install/docker-compose), [Plausible Community Edition](https://github.com/plausible/community-edition), [Supabase self-hosting with Docker](https://supabase.com/docs/guides/self-hosting/docker), [Cal.diy (Cal.com community edition) installation](https://cal.diy/installation), [Mattermost container deployment docs](https://docs.mattermost.com/deployment-guide/server/deploy-containers) (MEDIUM-HIGH; read via summarization, Mattermost pages show internally conflicting production guidance)
- Research-platform peers: [REDCap installation requirements](https://projectredcap.org/software/requirements/), [REDCap technical overview](https://projectREDCap.org/wp-content/resources/REDCapTechnicalOverview.pdf), [Beiwe backend wiki (old single-server AMI page)](https://github.com/onnela-lab/beiwe-backend/wiki/%5BOld%5D-Single-Server-AMI), [RADAR-Docker](https://github.com/RADAR-base/RADAR-Docker) (MEDIUM-LOW; search-result summaries, some pages dated)
- [Mailpit docs](https://mailpit.axllent.org/docs/) (HIGH for capabilities; default ports 1025/8025 are from general knowledge, not confirmed by the fetched page)
- Project inputs: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`

---
*Feature research for: self-hostable research-study platform (OpenWellness)*
*Researched: 2026-10-29*
