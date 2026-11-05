---
phase: 02-route-authentication-authorization
plan: 12
subsystem: testing
tags: [dev-seed, e2e, otp, jwt, refresh, uat, dockerignore]

requires:
  - phase: 02-route-authentication-authorization
    provides: enforced API and policy engine (02-03 to 02-10), mobile participant gate and bearer proof (02-11)
provides:
  - dev seed (admin, coach, participant, study) through the repository ports, idempotent, kept out of the API image
  - per-role CI flow: OTP sign-in, refresh (session restore), authorized call, sign-out, on fakes
  - 02-MANUAL-UAT.md with the D-10 recorded grep and the D-11 substitution
  - Phase 2 roadmap, requirement and STATE updates; both Phase 2 blockers resolved
affects: [phase-03-token-hardening, phase-11-bootstrap, phase-10-local-stack, phase-12-production-docs]

plan_head_before: 1e58301dc75a299fe76752d358d9de3a94cdbdef
plan_head_after: bf51573c24b949c9fb9882fce1851bc5e230ae83

actuals:
  tokens: 6000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Scripts under backend/api/scripts are loaded by path (runpy) in tests and excluded from the image"
    - "Seed reads every id back from the entity the port returns, because the Mongo adapter ignores a caller-chosen id"

key-files:
  created:
    - backend/api/scripts/dev_seed.py
    - .planning/phases/02-route-authentication-authorization/02-MANUAL-UAT.md
  modified:
    - backend/api/tests/test_e2e_roles_flow.py
    - backend/.dockerignore
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md

key-decisions:
  - "The seed completes a half-finished earlier run: the participant role pid is re-checked and saved on every run"
  - "The manual UAT uses weights for owner-scoped calls (A-12-1); other owner-scoped lists 500 on live Couchbase stores, a pre-existing gap"

patterns-established:
  - "CI and the manual UAT share one seed, so the CI flow exercises the data the UAT depends on"

requirements-completed: [AUTH-09]

coverage:
  - id: D1
    description: "Admin, coach and participant each sign in by OTP, restore via refresh, make an authorized call, and sign out (refresh with the revoked token is 401), on fakes"
    requirement: AUTH-09
    verification:
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_admin_flow, test_coach_flow, test_participant_flow"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dev seed creates one of each and is idempotent; revoke-all needs the bearer; participant gets 403 on the coach surface"
    requirement: AUTH-09
    verification:
      - kind: unit
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_seed_creates_one_of_each, test_seed_is_idempotent, test_revoke_all_needs_the_bearer, test_participant_cannot_reach_coach_surface_after_seed"
        status: pass
    human_judgment: false
  - id: D3
    description: "The seed script is excluded from the API image"
    verification:
      - kind: unit
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_seed_script_is_excluded_from_image"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-10 recorded grep shows only auth:* calls in both clients; roadmap research flags, success criterion 5, AUTH-09 and STATE blockers updated"
    verification:
      - kind: other
        ref: "grep checks in 02-12-PLAN.md Task 2 verify (all passed)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Manual UAT against the real dashboard, Android emulator and iOS simulator with a live local API"
    verification: []
    human_judgment: true
    rationale: "Needs live Couchbase, Mongo, Redis, an SMTP sink and two simulators; no tool can read an OTP on a device screen. Written, not run."

duration: 10min
completed: 2026-11-04
status: complete
---

# Phase 2 Plan 12: Per-role proof, dev seed and manual UAT Summary

**Idempotent dev seed plus a CI flow that signs admin, coach and participant in by real OTP, refreshes, calls, and signs out on fakes, with a written manual UAT carrying the D-10 recorded grep (only auth:* calls exist in either client).**

## Performance

- **Duration:** about 10 min
- **Started:** 2026-11-04T23:58Z (approximate; the start time was not captured at launch)
- **Completed:** 2026-11-05T00:08Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- `backend/api/scripts/dev_seed.py`: `seed_dev_data(*, users, studies, participants) -> SeedResult` and `main()`. Study, then users, then participant, then the participant user's `roles.participant.pid`; re-running changes nothing. No FastAPI import, no route, no secret.
- Eight new tests in `test_e2e_roles_flow.py` (18 passed in the file; the 10 earlier tests untouched). Tokens come from `auth:sendLoginCode` and `auth:verifyLoginCode` through `fake_email_sender.last_code`, never `token_for`. The refresh step is the dashboard's session restore.
- `backend/.dockerignore` excludes `api/scripts`, so the seed never ships in an image (tested).
- `02-MANUAL-UAT.md` with all nine required headings. D-10 grep output recorded verbatim; no non-auth path appeared, so there was nothing to stop and report.
- ROADMAP (Phase 2 research flag, Phase 10 and 12 flags, success criterion 5), REQUIREMENTS (AUTH-09) and STATE (both Phase 2 blockers resolved) updated.

## Task Commits

1. **Task 1 RED:** `b4eba2a` (test) failing per-role flows and seed tests
2. **Task 1 GREEN:** `0d94c53` (feat) dev seed and dockerignore entry
3. **Task 2:** `bf51573` (docs) D-10 evidence, manual UAT, roadmap, requirements, blockers

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Notes

- **RED:** 10 existing tests passed; `test_seed_script_is_excluded_from_image` failed on its assertion; the other 7 new tests errored in the `seed_dev` fixture with `FileNotFoundError` because `dev_seed.py` did not exist. Semantic assessment: the failure is for the intended reason (the seed is the thing missing), but 7 of 8 are fixture-load errors rather than assertion failures. This is not a `type: tdd` plan, so `check tdd-red-evidence` was not run; it would classify those as `fixture_or_load_failure`.
- **GREEN:** all 18 pass; full api suite 2422 passed (2414 plus 8).
- **REFACTOR:** none needed.

## Decisions Made

- The participant's pid is checked on every run rather than only at creation, so an interrupted first run is repaired by the second.
- Everything else followed the plan.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The tracer gate passed (the `<verify>` re-ran green before Task 2).

## Verification

- `cd backend/api && uv run --frozen pytest -q`: 2422 passed. core: 88 passed. scheduler: 4 passed.
- `uv run --frozen pyright`: 0 errors, 12 warnings. `check_no_fstring_n1ql.py`: exit 0.
- Dashboard in `node:22-bookworm-slim`: 140 passed. `git diff --stat 583f04f HEAD -- frontend/dashboard` prints nothing.
- Plan grep gates: `grep -c '^api/scripts' backend/.dockerignore` is 1; ROADMAP `recorded grep` >= 1, `logging-only pass` 0, `API_ENABLE_DOCS` >= 2; both files name the D-11 deviation; no `[Phase 2]` blocker remains; `git grep -l dev_seed -- '*.md'` lists nothing tracked.

## Known Stubs

None.

## Threat Flags

None. The seed adds no endpoint; T-02-31 is mitigated by the image exclusion, the lack of any route, and undeliverable `example.com` mailboxes.

## User Setup Required

Only for the manual UAT, which is written but not run and is for the developer: legacy Couchbase and Mongo instances, Docker (Redis and an SMTP sink), an Android emulator image and the iOS simulator. See `02-MANUAL-UAT.md`. Nothing was run against any Couchbase or Mongo instance and the seed was proven on fakes only.

## Next Phase Readiness

Phase 2 plans are all executed; the sign-off table in `02-MANUAL-UAT.md` is blank for the developer. Concurrent refresh with one token is unchanged (reuse detection still revokes the family until Phase 3's grace window, AUTH-08).

---
*Phase: 02-route-authentication-authorization*
*Completed: 2026-11-04*

## Self-Check: PASSED

- FOUND: backend/api/scripts/dev_seed.py, 02-MANUAL-UAT.md, backend/api/tests/test_e2e_roles_flow.py
- FOUND commits: b4eba2a, 0d94c53, bf51573 (ancestors of HEAD)
