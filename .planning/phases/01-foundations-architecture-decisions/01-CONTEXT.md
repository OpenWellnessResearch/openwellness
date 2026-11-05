# Phase 1: Foundations & Architecture Decisions - Context

**Gathered:** 2026-10-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Contributors get a trustworthy baseline before any Postgres schema exists:
- CI guards every PR (backend suites, pyright, dashboard checks, mobile host tests) — FOUND-01
- Datastore/Redis/shared settings defined once in `core`, loaded from one documented `.env` both under compose and when running `uvicorn`/`celery` directly — FOUND-02, FOUND-03
- No datastore types in the domain (`bson.ObjectId` out of `Participant` and anywhere else) — FOUND-04
- Users-by-email lookup and refresh sessions go through repository ports — FOUND-05
- Repository errors are honest: malformed id → 404, outage → 5xx logged via `logging` — FOUND-06
- ADRs for id format, timestamps, soft delete, token format, `owner` semantics, and the per-resource authorization policy table — FOUND-07

This phase **writes down** auth/token/soft-delete decisions; it does not implement route auth (Phase 2), asymmetric signing (Phase 3), or Postgres (Phase 4+).

</domain>

<decisions>
## Implementation Decisions

### Owner semantics & authorization policy (ADRs)
- **D-01:** `owner` semantics are **not pre-decided**. The researcher/planner must confirm from the legacy model, Couchbase/Mongo adapters, and tests whether `owner` holds the user id or the participant id (note: owner-scoped routes are `users/{user}/…`, while the token separately carries `roles.participant.pid`). The ADR records the finding plus any exceptions per entity. — **Reversibility:** one-way — once Postgres rows and PowerSync stream predicates key on it, changing it needs a data migration and stream rewrite.
- **D-02:** Coach authorization in v1 is **study-scoped**, not a bare role gate. This overrides the research default ("role gate in v1"); Phase 2 scope grows accordingly. — **Reversibility:** costly — every coach-reachable query and the Phase 6 sync policy depend on it.
- **D-03:** Coach study membership is stored **on the coach role in the user's roles dict** (e.g. `roles.coach.studies = [<study ids>]`) and carried as a signed token claim. No new membership entity. Admins manage it. The ADR must state how stale claims are handled (claims refresh at access-token renewal; document the maximum staleness window).
- **D-04:** Admins are **global** — they see and manage all studies.
- **D-05:** Denials: wrong owner / resource outside caller's scope → **404** (anti-enumeration); authenticated but missing role → **403**; anonymous → 401.
- **D-06:** The authorization policy ADR is a table at **resource × method granularity**: one row per resource module (`RESOURCE_MODULES`), columns for anonymous / participant-self / coach (in-study) / admin across get, list, create, patch, delete (archive), undelete, purge. Phase 2 implements it mechanically.

### Soft delete & retention (ADR)
- **D-07:** Archived records stay restorable via `:undelete` **indefinitely** until explicitly purged. No auto-expiry, no retention beat job.
- **D-08:** `:purge` is **admin-only**. Participants and coaches (within policy) may archive/undelete.
- **D-09:** Purge is a **hard delete** of the row (no scrub/tombstone). Sync removal relies on PowerSync's delete op. — **Reversibility:** one-way — purged research data cannot be recovered.
- **D-10:** Archived records **do not sync** to devices: streams filter `deleted_at IS NULL`, so archive removes the row from the device and undelete brings it back. Phase 6 verifies remove-on-transition.

### IDs, timestamps, tokens (ADRs)
- **D-11:** Primary keys are **text UUIDv4**, generated with stdlib `uuid.uuid4()`. Validation at the repository boundary accepts any valid UUID (any version); malformed ids → 404. ADR notes UUIDv7 as the upgrade path if the Phase 7 wearable load test shows index write pressure (switch costs nothing since validation is version-agnostic). — **Reversibility:** one-way — column type and client-generated ids are baked into Postgres schema and the mobile app.
- **D-12:** Timestamps stored as **`double precision` epoch seconds**, matching the domain's float epochs; wire stays RFC3339 via existing conversion helpers. — **Reversibility:** one-way — schema type across ~37 tables.
- **D-13:** Access tokens: **EdDSA (Ed25519) with `kid`**, published via JWKS; HS256 retired. PowerSync receives a separate minted token with `aud=powersync` (never the API secret). Phase 1 only records this; Phase 3 implements. — **Reversibility:** costly — dashboard, mobile, and PowerSync verify against it.
- **D-14:** ADR format: **short MADR files in `docs/adr/`**, one decision per file (Context / Decision / Consequences, ~1 page). The authorization policy table is its own ADR.

### CI & settings
- **D-15:** CI on **GitHub Actions** (no `.github/` exists yet). Every PR runs core/api/scheduler suites against fakes, pyright, the N1QL f-string lint, dashboard lint/typecheck/test/format:check, and mobile **JVM/Android host tests on Linux**. iOS simulator tests run nightly or on manual dispatch, not per PR.
- **D-16:** Pyright **errors fail** CI; warnings do not (keep the current `backend/pyrightconfig.json` downgrades).
- **D-17:** The single documented `.env` lives at the **repo root** (compose already uses it). Settings resolve it regardless of working directory (e.g. `uvicorn` launched from `backend/`), with an env-var override for the path.
- **D-18:** Precedence: **real environment > `.env` > code defaults** (pydantic-settings default).

### Claude's Discretion
- Exact name of the env-file override variable and how the repo root is located.
- CI job layout (one workflow vs several, caching, matrix).
- Exact exception types/mapping for FOUND-06 so long as malformed id → 404 and outage → logged 5xx.
- Shape of `RefreshSessionRepository` and `get_by_email` ports, and container split.
- Exact claim name for coach studies, provided it is in the ADR and consistent with D-03.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, research flag
- `.planning/REQUIREMENTS.md` — FOUND-01..07
- `.planning/PROJECT.md` — constraints (wire contract stable, legacy adapters keep working, tests without live infra)

### Research
- `.planning/research/SUMMARY.md` — resolved conflicts (ids, timestamps, token alg), open gaps (owner, coach authz, archive/purge)
- `.planning/research/PITFALLS.md` — owner-binding IDOR, port semantic drift, error swallowing
- `.planning/research/ARCHITECTURE.md` — container split, `bind_datastore`, port changes
- `.planning/codebase/CONCERNS.md` — unauthenticated routes, dead `require_principal`, `enforce_principal`
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md`

No external specs — remaining requirements captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/api/src/openwellness_api/config.py` and `backend/scheduler/src/openwellness_scheduler/config.py`: duplicated `CouchbaseSettings`/`SyncGatewaySettings`/`MongoSettings` (env prefixes `COUCHBASE_`, `SYNC_GATEWAY_`, `MONGO_`) — move into `core`; `API_`, `REDIS_`, `SMTP_`, `CELERY_` stay service-side except Redis (shared per FOUND-02). None set `env_file` today.
- `backend/api/src/openwellness_api/auth/service.py`: `_roles_list`, `_participant_pid` (`roles.participant.pid`) — the roles-dict shape that D-03 extends with `roles.coach.studies`.
- `backend/api/src/openwellness_api/common/timestamps.py`: epoch ↔ RFC3339 helpers backing D-12.
- `backend/core/scripts/check_no_fstring_n1ql.py`: existing lint to wire into CI.

### Established Patterns
- Repository ports in `core/application/repositories/` re-exported via `__init__.py`; adapters `cb_*`/`mongo_*`; composition only in `infrastructure/containers/repository_container.py`.
- Tests run on in-memory fakes (fakeredis, mongomock) — CI needs no live services.

### Integration Points
- `backend/core/src/openwellness_core/domain/models/participant.py`: `ObjectId` fields (`assigned_coach_id`, `user_id`, `study_id`) — FOUND-04 target.
- `backend/api/src/openwellness_api/auth/session_store.py` and `auth/service.py`: direct `pymongo` usage — FOUND-05 targets.
- `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py` (~lines 64-68): `print` + swallowed exceptions — FOUND-06 target.
- `docker-compose.yml` `env_file: .env` and `.env.example` at repo root — D-17.
- `backend/api/src/openwellness_api/deps/principal.py`: principal deps the policy ADR will reference.

</code_context>

<specifics>
## Specific Ideas

- UUIDv4 vs v7 was compared explicitly: v4 chosen for stdlib availability (Python 3.12 lacks `uuid7`) and no dependency on device clocks for offline-created ids; v7 recorded as an upgrade path for high-volume wearable tables.

</specifics>

<deferred>
## Deferred Ideas

- Auto-expiring archive retention window / purge beat job — not wanted for v1 (D-07).
- Dedicated StudyStaff/membership entity — rejected for v1 in favor of the roles dict (D-03); revisit if membership needs history or per-study roles.
- iOS simulator tests on every PR — nightly/manual only for now (D-15).
- UUIDv7 ids — upgrade path if wearable write volume demands it (D-11).

</deferred>

---

*Phase: 01-foundations-architecture-decisions*
*Context gathered: 2026-10-29*
