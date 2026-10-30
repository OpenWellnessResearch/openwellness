---
gsd_state_version: "1.0"
current_phase: 01
current_phase_name: Foundations & Architecture Decisions
status: verifying
stopped_at: Completed 01-11-PLAN.md
last_updated: "2026-10-30T14:42:59.257Z"
last_activity: 2026-10-30
last_activity_desc: Phase 01 execution started
state_head: a346beb77528f5960ee548166d202042ea6a3bb8
progress:
  total_phases: 12
  completed_phases: 0
  total_plans: 11
  completed_plans: 11
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-29)

**Core value:** Someone who has never seen the codebase can clone the repo, follow the docs, and end up with a secured, working OpenWellness instance (Postgres-backed, offline-sync capable) that participants' phones and the coach dashboard can use.
**Current focus:** Phase 01 — Foundations & Architecture Decisions

## Current Position

Phase: 01 (Foundations & Architecture Decisions) — EXECUTING
Plan: 11 of 11
Status: Phase complete — ready for verification
Last activity: 2026-10-30 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: `owner` semantics (user id vs participant id) must be confirmed from the legacy model before any Sync Stream predicate is written (Phase 6)
- [Phase 1]: Archive/purge semantics (restore window, retention) must be decided before Postgres soft-delete work (Phase 4)
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

Last session: 2026-10-30T14:42:59.238Z
Stopped at: Completed 01-11-PLAN.md
Resume file: None
