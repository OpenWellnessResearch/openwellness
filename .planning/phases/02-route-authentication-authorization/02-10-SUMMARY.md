---
phase: 02-route-authentication-authorization
plan: 10
subsystem: auth
tags: [route-enumeration, docs-gating, audit, mass-assignment, d-09, d-14]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: FloorRoute and strict bearer floor (02-03), POLICY and engine (02-04), all 36 modules on authorize (02-05 to 02-09)
provides:
  - create_app(*, lifespan=lifespan, settings=None) with docs, redoc and openapi off unless APISettings.enable_docs (API_ENABLE_DOCS)
  - build_test_app now builds through create_app, so tests see the real route table including /healthz
  - test_route_enumeration.py, test_docs_gating.py, test_audit_and_mass_assignment.py
  - README and .env.example matching the enforced behaviour; source invariants against the removed header and permissive mode
affects: [02-11, 02-12, phase 10 and 12 production docs]

actuals:
  tokens: 5600
  tasks: 3
  commits: 4

commits: 4
plan_head_before: 143429ccce30772885707dc46441302c5e996e69
plan_head_after: a8b9fbd0c0c3968c00113e6a4a41b89626a0b7b0

tech-stack:
  added: []
  patterns:
    - "Walk app.routes of the real app and collect failures into one sorted list compared to []"
    - "Sweep tests parametrized from POLICY (binding and the caller's cell), so a new row is covered without an edit"

key-files:
  created:
    - backend/api/tests/test_route_enumeration.py
    - backend/api/tests/test_docs_gating.py
    - backend/api/tests/test_audit_and_mass_assignment.py
  modified:
    - backend/api/src/openwellness_api/main.py
    - backend/api/src/openwellness_api/config.py
    - backend/api/tests/conftest.py
    - backend/api/tests/test_source_invariants.py
    - backend/api/README.md
    - .env.example

key-decisions:
  - "Docs gating sets docs_url, redoc_url and openapi_url all to None; with only the first two off, /openapi.json is still served"
  - "Exempt set is checked as exactly /healthz plus auth.build_router() routes, by FloorRoute membership, not by path prefix"
  - "Audit sweep reads the stored entity as well as the response, so the persisted updated_by is what is proven"

requirements-completed: [AUTH-01, AUTH-02, AUTH-06]

coverage:
  - id: E1
    description: "Anonymous, unparseable-body and six bad-bearer requests to all 254 non-exempt method-and-path pairs on the real app answer 401"
    requirement: AUTH-01
    verification:
      - kind: integration
        ref: "backend/api/tests/test_route_enumeration.py#test_anonymous_gets_401_on_every_route"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_route_enumeration.py#test_anonymous_unparseable_body_gets_401_on_every_route"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_route_enumeration.py#test_bad_bearer_gets_401_on_every_route"
        status: pass
    human_judgment: false
  - id: E2
    description: "Every resource route carries exactly one authorize whose module and op match the router, method and path; all 36 modules covered; exempt set is exact"
    requirement: AUTH-02
    verification:
      - kind: integration
        ref: "backend/api/tests/test_route_enumeration.py#test_every_resource_route_has_one_authorize"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_route_enumeration.py#test_all_36_modules_are_rolled_out"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_route_enumeration.py#test_exempt_routes_are_exact"
        status: pass
    human_judgment: false
  - id: E3
    description: "D-09: /docs, /redoc and /openapi.json are 404 by default and served only with API_ENABLE_DOCS on"
    requirement: AUTH-01
    verification:
      - kind: integration
        ref: "backend/api/tests/test_docs_gating.py#test_docs_off_by_default"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_docs_gating.py#test_docs_on_when_enabled"
        status: pass
    human_judgment: false
  - id: E4
    description: "AUTH-06: a forged X-Principal-Id changes nothing on create or patch for any allowed caller on any owner-bound row; patch cannot move owner, study or audit fields"
    requirement: AUTH-06
    verification:
      - kind: integration
        ref: "backend/api/tests/test_audit_and_mass_assignment.py#test_forged_header_ignored_on_create"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_audit_and_mass_assignment.py#test_forged_header_ignored_on_patch"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_audit_and_mass_assignment.py#test_patch_cannot_move_record_any_row"
        status: pass
    human_judgment: false
  - id: E5
    description: "README and .env.example describe the enforced behaviour and the removed header and setting cannot reappear"
    requirement: AUTH-01
    verification:
      - kind: integration
        ref: "backend/api/tests/test_source_invariants.py#test_no_principal_header_or_permissive_mode_left"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_source_invariants.py#test_env_example_turns_docs_on_with_a_warning"
        status: pass
    human_judgment: false

duration: about 20 min
completed: 2026-11-04
---

# Phase 2 Plan 10: Enforcement proof across the real app Summary

**The phase's first success criterion is now a green test on the real wiring: every one of the 254 non-exempt method-and-path pairs answers 401 to an anonymous, bad-bearer or unparseable-body request, every resource route carries one matching `authorize` across all 36 modules, API docs are off by default, and a forged `X-Principal-Id` cannot change an audit field or move a record on any owner-bound row.**

## Accomplishments

- `create_app(*, lifespan=lifespan, settings=None)`; `APISettings.enable_docs` (default false) turns off `/docs`, `/redoc` and `/openapi.json` together. `build_test_app` calls `create_app(lifespan=None, settings=APISettings(enable_docs=False))`, so the harness no longer assembles its own `FastAPI`.
- `test_route_enumeration.py` (16 tests) and `test_docs_gating.py` (2 tests): both anonymous walks assert at least 254 pairs, failures collected sorted and compared to `[]`.
- `test_audit_and_mass_assignment.py`: 189 cases parametrized from `POLICY`.
- README `deps/` bullet rewritten (strict bearer, no fallback), `authz/` bullet and `API_ENABLE_DOCS` row added, `{user}` documented as a participant id; the removed setting dropped from the `API_AUTH_*` list. `.env.example` gains `API_ENABLE_DOCS=true` with the deployed-instance warning.

## Task Commits

1. Task 1 (tracer) RED `7b78422` (6 of 18 failing on the planned assertions). GREEN `472b622`. Tracer gate: 18 passed, then the full api suite passed; verified end-to-end, expanding.
2. Task 2 `164b54b`: 189 passed. The tests passed on first run, no production defect found.
3. Task 3 `a8b9fbd`.

## TDD Gate Compliance

Task 1 went RED then GREEN as above, judged by the pytest report. Task 2 had no RED commit: it is a test-only sweep over behaviour built in earlier plans, and it passed immediately, which is the expected result of a regression sweep rather than new behaviour. `gsd_run check tdd-red-evidence` was not run (`type: execute`).

## Deviations from Plan

None - plan executed exactly as written. The wave-boundary full-suite run surfaced no failure in any router from plans 02-05 to 02-09, so no route or matrix expectation was changed or exempted.

## Known Stubs

None added. The engine's `self-member-conversation` match-nothing shortcut from 02-04 is unchanged.

## Issues Encountered

- First GREEN run had one failure in my own test: the unparseable-body walk passed `headers` twice. Fixed in the same commit.
- Full api suite takes about 95 s (the plan estimated about a minute); disclosed in the plan as expected.
- `actuals.tokens` is chars/4 over the `backend/` and `.env.example` diff (22,245 characters), against an estimate of 50,000.

## Flagged assumptions

Edge AUTH-06 stays surfaced: forged header, body-supplied study and owner on create and patch are covered here; anything beyond that is for the developer to flag. The `.env.example` follow-up (T-02-28, docs on in a template copied to VMs) is accepted and left to plan 02-12.

## Threat Flags

None. No new endpoints; docs gating reduces exposure. T-02-25, T-02-26 and T-02-27 are covered by the named tests.

## Verification

- Per suite: core 88 passed, api 2414 passed (2205 before), scheduler 4 passed.
- Pyright: 0 errors, 12 warnings. `check_no_fstring_n1ql.py` exits 0.
- Commits landed on `main` (`branching_strategy=none`, sequential dispatch).

## Self-Check: PASSED

- FOUND: backend/api/tests/test_route_enumeration.py, test_docs_gating.py, test_audit_and_mass_assignment.py
- FOUND commits: 7b78422, 472b622, 164b54b, a8b9fbd
