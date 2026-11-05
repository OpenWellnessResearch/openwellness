---
phase: 02-route-authentication-authorization
plan: 02
subsystem: auth
tags: [authorization, policy-table, adr, parity-test, d-14, d-15]
status: complete

requires:
  - phase: 01-local-dev-stack-and-backend-baseline
    provides: ADR 0005 owner semantics, ADR 0007 policy table, the 36-row parity test
provides:
  - openwellness_api.authz.policy with OPS, Row, POLICY (36 rows) and CUSTOM_OPS
  - parity tests proving POLICY equals ADR 0007 per cell and ADR 0005 per binding
  - ADR 0007 "Phase 2 amendment" recording D-06 to D-09 and every open-decision default
  - AUTH-05 and Phase 2 success criterion 3 naming the D-08 empty-list exception
affects: [02-04 authz engine consumes POLICY, 02-10 route structure test consumes CUSTOM_OPS, phase 6 sync policy]

actuals:
  tokens: 4800
  tasks: 3
  commits: 4

plan_head_before: 945276e629ef5417276124942d9afa3f27813120
plan_head_after: 8be59f7b058e8a414bd006efe4b8e2564a0fc2c4

tech-stack:
  added: []
  patterns:
    - "Policy as one data table keyed by resource module, no router factory (D-14)"
    - "ADR is the written contract; a test parses it and compares to code, the API never reads it (D-15)"

key-files:
  created:
    - backend/api/src/openwellness_api/authz/__init__.py
    - backend/api/src/openwellness_api/authz/policy.py
  modified:
    - backend/api/tests/test_adr_policy_table.py
    - docs/adr/0007-authorization-policy-table.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "POLICY rows use named frozensets (_NONE, _GET, _READ, _READ_PATCH, _SIX, _ALL) for the ADR data classes; the table is data, no helpers"
  - "binding is None for the eight rows outside ADR 0005's table, so the binding test checks both directions"
  - "The amendment uses bullets only, because any backticked lowercase table row would break the ROW regex and the 36-row assertion"

patterns-established:
  - "Change a policy cell in the ADR or in Python without the other and test_policy_matches_adr_0007 fails"

requirements-completed: [AUTH-02, AUTH-04, AUTH-05]

coverage:
  - id: D1
    description: "POLICY equals ADR 0007 for all 36 rows (route, scope, self/coach/admin ops) and ADR 0005 for binding"
    requirement: AUTH-05
    verification:
      - kind: unit
        ref: "backend/api/tests/test_adr_policy_table.py#test_policy_matches_adr_0007"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_adr_policy_table.py#test_binding_matches_adr_0005"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_adr_policy_table.py#test_policy_row_diff_detects_a_changed_cell"
        status: pass
    human_judgment: false
  - id: D2
    description: "Only admin holds purge, and POLICY keys are exactly the resource modules"
    requirement: AUTH-04
    verification:
      - kind: unit
        ref: "backend/api/tests/test_adr_policy_table.py#test_only_admin_holds_purge"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_adr_policy_table.py#test_policy_keys_are_resource_modules"
        status: pass
    human_judgment: false
  - id: D3
    description: "ADR 0007 records the Phase 2 amendment with all 14 decisions and the D-06 refinement"
    requirement: AUTH-02
    verification:
      - kind: unit
        ref: "backend/api/tests/test_adr_policy_table.py#test_phase_2_amendment_is_recorded"
        status: pass
    human_judgment: false
  - id: D4
    description: "AUTH-05 and success criterion 3 name the D-08 empty-200 exception"
    requirement: AUTH-05
    verification:
      - kind: command
        ref: "grep -c 'answers an empty 200 and exposes no data' .planning/REQUIREMENTS.md .planning/ROADMAP.md"
        status: pass
    human_judgment: true
    rationale: "Wording quality of a requirement is a judgment; the grep proves only presence"

duration: 15 min
completed: 2026-11-04
---

# Phase 2 Plan 02: Policy table in Python, proven equal to ADR 0007 Summary

**36-row `POLICY` table in `authz/policy.py` that CI proves equal to ADR 0007 cell by cell and to ADR 0005 on owner binding, with ADR 0007 amended for D-06 to D-09 and the D-08 empty-200 exception written into AUTH-05.**

## Accomplishments

- `authz/policy.py`: `OPS`, frozen `Row`, `POLICY` (one row per `RESOURCE_MODULES` entry), `CUSTOM_OPS` (`conversation:search` is list, `study:lookup` is get). Nothing enforces it yet; plan 02-04 does.
- `test_adr_policy_table.py` parses ADR 0007 and 0005 and compares them to `POLICY`; the comparator has its own test so the parity check cannot be vacuous. 6 new tests plus the 2 existing ones.
- ADR 0007 gained a second `Amended:` bullet and a `## Phase 2 amendment` section with 14 bold-led bullets (D-06, D-07, D-08, D-09, segment-less requests (A1, the D-06 refinement), top-level lists, patch keys, custom methods, staleness, conversation membership, archived records, participant group lists, empty out-of-study list, group members).
- AUTH-05 and Phase 2 success criterion 3 now say a coach's owner-scoped list for an out-of-study participant with no records answers an empty 200 and exposes no data.

## TDD Gate Compliance

- RED (`f91591b`): the target `test_policy_matches_adr_0007` failed on its assertion with 36 `missing from POLICY` diffs against a stub with an empty `POLICY`. The stub was needed so the import resolves; without it the run would be a load failure. Semantic assessment: target executed, failed on the planned assertion for the intended reason. `test_policy_row_diff_detects_a_changed_cell` passed in RED by design, since it exercises only the test-side comparator. `gsd_run check tdd-red-evidence` was not run: pytest output is not among its supported report formats.
- GREEN (`5ed7173`): `POLICY` filled; 7 passed.
- REFACTOR: none.

## Task Commits

1. Task 1 RED: `f91591b` test(02-02): add failing ADR 0007 and 0005 policy parity tests
2. Task 1 GREEN: `5ed7173` feat(02-02): add the POLICY table mirroring ADR 0007
3. Task 2: `ab9509a` docs(02-02): amend ADR 0007 with phase 2 policy decisions
4. Task 3: `8be59f7` docs(02-02): name the D-08 empty-list case in AUTH-05 and success criterion 3

## Deviations from Plan

None - plan executed exactly as written. `POLICY` rows were transcribed by a throwaway script (kept outside the repo) that read the ADR tables and emitted the Python, then verified by the parity test.

## Decisions

Developer-confirmed defaults A1, A3, A4, A5, OQ1, OQ3, A-02-1 and A-09-2 are now written in ADR 0007. A2 (top-level list filtering) and A-09-1 (participant group list meaning) remain planner defaults, recorded as such in the amendment.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema; the only runtime change is an unreferenced data module.

## Verification

Per-suite: core 88 passed, api 256 passed (250 + 6 new), scheduler 4 passed; pyright 0 errors; `check_no_fstring_n1ql.py` exit 0. No `open(` or `read_text` under `authz/`.

Note: commits landed on `main` (a protected branch by default config) because the orchestrator set `branching_strategy=none` and dispatched sequentially.

## Self-Check: PASSED

- FOUND: backend/api/src/openwellness_api/authz/__init__.py
- FOUND: backend/api/src/openwellness_api/authz/policy.py
- FOUND commits: f91591b, 5ed7173, ab9509a, 8be59f7
