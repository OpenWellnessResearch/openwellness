---
phase: 01-foundations-architecture-decisions
plan: 08
subsystem: docs
tags: [adr, owner, authorization, sync-gateway, powersync]

requires:
  - phase: 01-foundations-architecture-decisions
    provides: ADR format and index (plan 01-07)
provides:
  - ADR 0005 owner semantics (Accepted), owner = participant id
  - Entity classification table (28 rows, four data classes) consumed by ADR 0007
affects: [01-09, phase-02-auth, phase-04-postgres-schema, phase-06-powersync]

actuals:
  tokens: 6000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns: ["Developer testimony recorded as data-level evidence when no legacy data sample exists"]

key-files:
  created:
    - docs/adr/0005-owner-semantics.md
  modified:
    - docs/adr/README.md

key-decisions:
  - "owner = participant id (option-participant), derived from the legacy Sync Gateway owner-to-channel rule; Phase 2 binds token participant claim to {user} on users/{user}/... and sub on top-level users/{user}"
  - "study_settings owner holds a study id; conversation and participant_group are multi-participant documents where owner is not routing-relevant and access is by membership"
  - "Open point for Phase 6: conversation and participant_group streams need a membership-based rule, not an owner predicate (not decided in this ADR)"

patterns-established:
  - "Classification table rows for exempt types use owner holds = 'not routing-relevant (membership)'"

requirements-completed: []

plan_head_before: bb363a93c0a8f13fe574c3cafa9634132c7fae2f
plan_head_after: 9f2afb9aa6c86ba825c9e8974c9e71f4620a4844
commits: 2
status: complete
---

# Phase 1 Plan 08: Owner Semantics Summary

**ADR 0005 Accepted: `owner` is the participant id (legacy Sync Gateway owner channel), with study_settings, conversation and participant_group as documented exceptions.**

## Accomplishments

- Evidence sweep and draft ADR (Task 1, commit 8214933): file:line evidence from domain models, adapters, auth and tests; 28-row classification table verified against introspected RESOURCE_MODULES.
- Developer checkpoint (Task 2): chose option-participant and supplied data-level testimony about the legacy Couchbase deployment.
- Finalized ADR 0005 as Accepted (Task 3, commit 9f2afb9): Decision states binding claim per route family, Phase 6 predicate, and the three exceptions; testimony added to Evidence; conversation and participant_group rows corrected; all unconfirmed markers resolved; README index set to Accepted.

## Task Commits

1. Task 1: 8214933 (draft, Proposed)
2. Task 2: checkpoint, no commit
3. Task 3: 9f2afb9 (Accepted)

## Deviations from Plan

None to the plan's logic. Note: the plan's classification check rejects nothing here, but the checkpoint required a non-id `owner holds` value for conversation and participant_group; the wording `not routing-relevant (membership)` passes the check (it validates only row set, cell count and data class) and keeps the meaning explicit. Accepted-as-drafted rows now cite "accepted as drafted" in place of "(unconfirmed)".

## Issues Encountered

None.

## Known Stubs

None.

## Open Points

- FOUND-07 is left incomplete: ADR 0006 and 0007 (plan 01-09) are still pending, so the requirement is not marked complete.
- Phase 6 must define a membership-based stream rule for `conversation` and `participant_group`; not decided here.

## Self-Check: PASSED

- docs/adr/0005-owner-semantics.md and docs/adr/README.md exist; commits 8214933 and 9f2afb9 are on the branch.
- Index check, Accepted/Confirmed/unconfirmed gates and `classification-ok 28` all passed.
