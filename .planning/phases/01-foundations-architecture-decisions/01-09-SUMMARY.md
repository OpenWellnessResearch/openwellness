---
phase: 01-foundations-architecture-decisions
plan: 09
subsystem: docs
tags: [adr, authorization, coach, study-scope, policy-table]

requires:
  - phase: 01-foundations-architecture-decisions
    provides: ADR 0005 owner semantics and entity classification (plan 01-08), ADR 0004 claim set
provides:
  - ADR 0006 coach study scope (roles.coach.studies stored, coach_studies claim, 930 s staleness bound)
  - ADR 0007 authorization policy table (36 rows, six scope predicates, caller-independent study-binding write rule)
  - REQUIREMENTS.md AUTH-05 and ROADMAP Phase 1/2 wording aligned with study-scoped coach access (D-02)
affects: [phase-02-auth, phase-06-powersync]

actuals:
  tokens: 11000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns: ["Machine-checkable ADR tables validated against RESOURCE_MODULES", "Membership rows recorded as explicit exception when the rule table cannot express them"]

key-files:
  created:
    - docs/adr/0006-coach-study-scope.md
    - docs/adr/0007-authorization-policy-table.md
  modified:
    - docs/adr/README.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Coach studies live at roles.coach.studies on the User, admin-managed, minted as the coach_studies claim; no membership entity; admins global; legacy Admin.study_ids not read; staleness at most 900 s + 30 s"
  - "ADR 0007 denial codes: anonymous 401, missing role 403, wrong owner or outside study 404; scope applied before filter=; purge admin-only"
  - "Participant study is derived from the Participant record (self-study), not claimed; Device has no study id so its coach cell is none"
  - "study-binding is a caller-independent write rule: study_id derived from the owner's Participant, differing supplied study_id gets 404, owner and study_id immutable on patch"
  - "conversation and participant_group (ADR 0005 owner not routing-relevant, membership) get participant-self none and coach scoped by record study_id alone, until a membership predicate is decided"

patterns-established:
  - "Policy cells name a scope predicate built only from signed claims plus stored fields"

requirements-completed: [FOUND-07]

plan_head_before: eb42999afc3bcb48842c9d099c0535eb455b6028
plan_head_after: e054b37ddf6fe23ccb08bbe4a33822a288fb3415
commits: 3
status: complete
---

# Phase 1 Plan 09: Coach Study Scope and Authorization Policy Table Summary

**ADRs 0006 and 0007 settle study-scoped coach access (`coach_studies` claim) and a 36-row resource-by-method policy table with a computable scope predicate behind every allowed cell.**

## Accomplishments

- ADR 0006 records where coach studies are stored, how they reach the token, who edits them, and the staleness bound (900 s access TTL plus 30 s leeway).
- ADR 0007 holds the rule table (ADR 0005 data class to cells), six scope predicates, the `study-binding` write rule, the 36-row Policy table and the unauthenticated endpoints.
- REQUIREMENTS.md AUTH-05 now absorbs the former v2 AUTHZ-01, and ROADMAP.md Phase 1 and Phase 2 coach wording matches D-02.
- All FOUND-07 ADRs (0001 to 0007) now exist; FOUND-07 was already ticked in REQUIREMENTS.md by plan 01-07, confirmed rather than re-marked.

## Task Commits

1. Task 1, ADR 0006: bdc344b
2. Task 2, ADR 0007: e7e6452
3. Task 3, requirements and roadmap alignment: e054b37

## Verification

- Index check: 7 ADR files, none bad or missing.
- Policy check: `policy-ok 36`.
- Scope check: `scope-ok 6 36`.
- Caveat check: `adr-0007-caveats-ok`.
- Requirements alignment: `reqs-aligned`.
- Human check (developer review of the fixed rows) is outstanding for the end-of-phase review.

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Membership exception for conversation and participant_group**
- **Found during:** Task 2 (orchestrator note and ADR 0005 `owner holds = not routing-relevant (membership)`)
- **Issue:** The plan's rule table maps study-content rows to `self-owner`/`self-study` and resolves the owner to a Participant on coach writes. For `conversation` and `participant_group` ADR 0005 says owner carries no routing meaning, so neither the owner binding nor owner-to-Participant resolution applies, and a membership predicate is not computable (a seventh predicate would also break the plan's `scope-ok 6 36` check).
- **Fix:** participant-self is `none` on these two rows (Scope names only `coach-study`); the coach cell follows study-content scoped by the record's `study_id` alone; a bullet in Write rules states that study_id must be non-empty and, for a coach, in coach_studies; Decision and Consequences state the exception and that a later ADR amendment widens participant-self once a membership predicate exists.
- **Files modified:** docs/adr/0007-authorization-policy-table.md
- **Commit:** e7e6452

**Total deviations:** 1 (Rule 2). **Impact:** participants get no access to conversations or participant groups until a membership ADR amendment; this matches ADR 0005's open point and fails closed.

## Accepted Risks

- T-01-33 (plan 01-05): duplicate-email `POST /v1/users` returns 409 ALREADY_EXISTS and so reveals registration. Recorded in ADR 0007 Consequences; after Phase 2 the user row grants create to admin only, and no production docs ship before route auth.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- docs/adr/0006-coach-study-scope.md and docs/adr/0007-authorization-policy-table.md exist.
- Commits bdc344b, e7e6452 and e054b37 are on the branch.
- All plan verification commands passed (see Verification).
