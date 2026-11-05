---
gsd_state_version: "1.0"
current_phase: 02
current_phase_name: Route Authentication & Authorization
status: verifying
stopped_at: Completed 02-12-PLAN.md
last_updated: "2026-11-05T00:07:57.372Z"
last_activity: 2026-11-04
last_activity_desc: Phase 02 execution started
state_head: bf51573c24b949c9fb9882fce1851bc5e230ae83
progress:
  total_phases: 12
  completed_phases: 1
  total_plans: 23
  completed_plans: 23
  percent: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-30)

**Core value:** Someone who has never seen the codebase can clone the repo, follow the docs, and end up with a secured, working OpenWellness instance (Postgres-backed, offline-sync capable) that participants' phones and the coach dashboard can use.
**Current focus:** Phase 02 — Route Authentication & Authorization

## Current Position

Phase: 02 (Route Authentication & Authorization) — EXECUTING
Plan: 12 of 12
Status: Phase complete — ready for verification
Last activity: 2026-11-04 — Phase 02 execution started

Progress: [█░░░░░░░░░] 8%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 11 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 5 min | 3 tasks | 4 files |
| Phase 01 P02 | 20min | 2 tasks | 10 files |
| Phase 01 P03 | 15min | 2 tasks | 5 files |
| Phase 01 P07 | 8min | 3 tasks | 5 files |
| Phase 01 P04 | 12 min | 2 tasks | 7 files |
| Phase 01 P08 | 20min | 3 tasks | 2 files |
| Phase 01 P10 | 5min | 2 tasks | 3 files |
| Phase 01 P05 | 25min | 3 tasks | 10 files |
| Phase 01 P09 | 12 min | 3 tasks | 5 files |
| Phase 01 P06 | 15min | 2 tasks | 5 files |
| Phase 01 P11 | 15min | 2 tasks | 8 files |
| Phase 02 P01 | 15 min | 2 tasks | 5 files |
| Phase 02 P02 | 15 min | 3 tasks | 6 files |
| Phase 02 P03 | 12 min | 2 tasks | 9 files |
| Phase 02 P04 | 50 min | 3 tasks | 8 files |
| Phase 02 P05 | 25 min | 3 tasks | 14 files |
| Phase 02 P06 | 25 min | 3 tasks | 14 files |
| Phase 02 P07 | 25 min | 2 tasks | 6 files |
| Phase 02 P08 | 15 min | 2 tasks | 5 files |
| Phase 02 P09 | 25 min | 3 tasks | 6 files |
| Phase 02 P10 | 20 min | 3 tasks | 9 files |
| Phase 02 P11 | 12 min | 2 tasks | 6 files |
| Phase 02 P12 | 10 min | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: All auth enforcement (Phases 2-3) completes before production deployment docs (Phase 12)
- [Roadmap]: Postgres Phase 4 depends on Phases 1 and 3 so the Postgres refresh store honors the grace window; phases 1–6 run in sequence
- [Roadmap]: The PowerSync sync-credentials endpoint (Phase 6) depends on `kid`-signed asymmetric tokens and JWKS (Phase 3)
- [Roadmap]: The self-host kit (Phases 10-11) depends on the PowerSync backend (Phase 6), not on the mobile phases
- [Roadmap]: Cross-category placements: DOCS-09 (PowerSync license) in Phase 6, DOCS-05 (config reference) in Phase 10, KIT-08 (audit table) in Phase 11
- [Phase 01]: Dashboard CI pinned to Node 22 (Node 25+ built-in localStorage breaks jsdom suites); pyright scope left at core only
- [Phase 01]: Env file resolved at repo root via docker-compose.yml marker; OPENWELLNESS_ENV_FILE overrides; precedence env > .env > defaults
- [Phase 01]: 01-03: Mongo malformed id is not-found; datastore errors propagate; API catch-all returns generic logged 500 INTERNAL
- [Phase 01]: Primary keys are text UUIDv4 via uuid.uuid4(); validation accepts any UUID version (ADR 0001)
- [Phase 01]: Timestamps stored as double precision epoch seconds; wire stays RFC 3339 (ADR 0002)
- [Phase 01]: Archive sets deleted_at; undelete indefinite; purge admin-only hard delete (ADR 0003)
- [Phase 01]: Access tokens EdDSA Ed25519 with kid and JWKS; separate aud=powersync token; HS256 retired; no participant study claim (ADR 0004)
- [Phase 01]: 01-04: Mongo participant adapter owns ObjectId coercion in _to_doc; empty/malformed studyId refused (404), never stored
- [Phase 01]: ADR 0005: owner = participant id (legacy Sync Gateway owner channel); Phase 2 binds participant claim to {user} on users/{user}/... and sub on top-level users/{user}; exceptions: study_settings (study id), conversation and participant_group (membership-based, open point for Phase 6)
- [Phase 01]: 01-10: compose environment overrides carry redis service hostnames; .env keeps localhost so one file serves both
- [Phase 01]: 01-05: DuplicateEntityException lives in application, re-exported by adapters.exceptions (LimitExceededException placement); messages name the collection only
- [Phase 01]: ADR 0006/0007: study-scoped coach access via coach_studies claim; 36-row policy table; conversation and participant_group participant-self none until membership predicate (ADR 0005 open point)
- [Phase 01]: 01-06: RefreshSession record lives in the port module; Mongo adapter takes caller-supplied collection and keeps today's document/index names
- [Phase 01]: 01-11: AuthSettings.refresh_collection kept; lifespan overrides RepositoryContainer.refresh_session_collection so customized deployments keep live sessions
- [Phase 02]: Staff (coach/admin) login eligibility ignores verified_id; participant-only users still need verified_id and pid (D-01, D-03)
- [Phase 02]: Refresh keeps consume_for_rotation ahead of the eligibility gate so an ineligible user's presented token is already consumed (A-01-3)
- [Phase 02]: POLICY table is data keyed by resource module; ADR 0007 Phase 2 amendment records D-06 to D-09 and the 2026-11-04 developer decisions
- [Phase 02]: 02-03: Bearer floor is FloorRoute (APIRoute subclass wrapping the handler), not a router dependency, because FastAPI parses the body before solving dependencies
- [Phase 02]: 02-03: 401 carries no WWW-Authenticate header; missing auth container surfaces as 500, never an anonymous pass
- [Phase 02]: 02-04: authorize/Access engine decides from POLICY; a handler that skips check_record/scope_list fails open for deferred columns, so every router plan must stay in the matrix gate
- [Phase 02]: 02-04: self-study treats a no-segment list or create as vacuous without reading the Participant (A1); membership-row create denial happens in stamp_create
- [Phase 02]: goal list scopes the unfiltered owner list before filter=, then intersects the kind query with the scoped ids so filter= can only narrow
- [Phase 02]: 02-06: matrix sends integer week bounds for condition (parse_int range) rather than changing the wire contract
- [Phase 02]: 02-06: message list scopes the unfiltered owner list, then intersects the subtype/condition query
- [Phase 02]: 02-07: a body studyId on a study_settings create is dropped by the wire schema (extra=ignore), so the row binds to the path study; no 404
- [Phase 02]: 02-07: MongoStudyRepository.get_by_name escapes the name with re.escape (A-07-1); lookup stays exact and case-insensitive
- [Phase 02]: 02-08: duplicate-email oracle closed by the admin-only user create cell (authorize runs before the handler), not by changing the 409 handler
- [Phase 02]: 02-09: participant_group list applies scope_list before the created_at window so a coach outside the study gets the D-08 404 whatever the window
- [Phase 02]: 02-10: API docs gated by API_ENABLE_DOCS (default off); docs_url, redoc_url and openapi_url all set to None, since the UI urls alone still serve /openapi.json
- [Phase 02]: 02-10: build_test_app builds through create_app, so the enumeration test walks the real route table; exempt set is exactly /healthz plus auth router routes
- [Phase 02]: 02-11: mobile NotParticipant gate in persistVerified fires only on null/blank participant, before saveTokens, with best-effort refresh revoke; D-11 mobile proof is a MockEngine test (OQ5)
- [Phase 02]: 02-12: dev seed re-checks the participant pid on every run so an interrupted run is repaired; CI and the manual UAT share one seed

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 6]: Conversation and participant-group membership predicate (ADR 0005 open point) must be defined before their Sync Stream rules
- [Phase 4]: The Postgres refresh-session store must honor the refresh grace window from Phase 3 (cover it in the contract suite)
- [Phase 6]: PowerSync Postgres bucket storage is Beta; spike it, with a second postgres container as fallback
- [Phase 7]: Wearable sync volume is unproven; the 90-day load test may force windowed streams (a carve-out from "sync full participant data")
- [Phase 8]: PowerSync Kotlin SDK 1.14.1 build and iOS runtime are unverified on the current toolchain

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-05T00:07:57.260Z
Stopped at: Completed 02-12-PLAN.md
Resume file: None
