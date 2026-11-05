---
phase: 01-foundations-architecture-decisions
plan: 01
subsystem: infra
tags: [github-actions, ci, pytest, pyright, vitest, gradle, uv]

requires: []
provides:
  - "CI workflow: backend, dashboard and mobile jobs on every PR and push to main"
  - "Nightly / manual iOS simulator workflow"
  - "Green baseline: pyright 0 errors, api suite 0 failed"
affects: [all later phases, branch protection for main]

actuals:
  tokens: 1900
  tasks: 3
  commits: 3
plan_head_before: 5969fad7b6f565efa34db99c04d78929d49e5c9e
plan_head_after: 6f63234c1c0e6f47a37950840263d065547b5433
commits: 3

tech-stack:
  added: [GitHub Actions workflows]
  patterns: ["SHA-pinned actions with version comment", "independent jobs, no needs:", "if: !cancelled() gated on install step"]

key-files:
  created: [.github/workflows/ci.yml, .github/workflows/ios-nightly.yml]
  modified: [backend/core/tests/test_smoke.py, backend/api/tests/test_session_store.py]

key-decisions:
  - "Dashboard CI pinned to Node 22: Node 25+ built-in localStorage breaks the jsdom suites"
  - "pyright scope left as configured (core only); widening to api/scheduler surfaces 14 errors and is out of this phase"

requirements-completed: [FOUND-01]

coverage:
  - id: D1
    description: "Backend job runs core/api/scheduler pytest, pyright and N1QL lint; all green locally on the current tree"
    requirement: FOUND-01
    verification:
      - kind: other
        ref: "cd backend && uv run --frozen pyright (0 errors); core 74, api 187, scheduler 4 passed; check_no_fstring_n1ql.py exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dashboard job: lint, typecheck, test (Node 22), format:check all green locally"
    requirement: FOUND-01
    verification:
      - kind: other
        ref: "npm run lint/typecheck/format:check exit 0; docker node:22-bookworm-slim npm test: 16 files, 140 tests passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mobile job runs ./gradlew testAndroidHostTest; never executed yet (no JDK/Android SDK locally)"
    requirement: FOUND-01
    verification: []
    human_judgment: true
    rationale: "First run is the Mobile job on the CI pull request; gates merge"
  - id: D4
    description: "Failing check shows on the PR and a deliberately broken test turns Backend red"
    requirement: FOUND-01
    verification: []
    human_judgment: true
    rationale: "Needs a pushed branch and PR, which the user has not approved yet"

duration: 5min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 01: CI Summary

**GitHub Actions CI with independent backend (pytest x3, pyright, N1QL lint), dashboard (Node 22) and mobile (testAndroidHostTest) jobs, plus a nightly iOS workflow, on a tree made green first**

## Performance

- **Duration:** about 5 min of this resumed session
- **Completed:** 2026-10-30T12:53Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Backend baseline fixed: pyright 3 errors to 0 (TypeVar-generic roundtrip helpers), api suite 1 failed to 0 failed (fixed far-future expiry).
- `ci.yml`: triggers `pull_request` plus push to `main`, no paths filters, `contents: read`, concurrency group `ci-<PR number or ref>` with cancel-in-progress, no `needs:`, each check step gated on the install step with `!cancelled()`.
- `ios-nightly.yml`: cron `0 6 * * *` plus `workflow_dispatch` only, macos-latest.

## Task Commits

1. **Task 1: Backend CI job, green baseline** - `205c6cb` (feat)
2. **Task 2: Dashboard and mobile jobs** - `b0d2af1` (feat)
3. **Task 3: iOS nightly workflow** - `6f63234` (feat)

**Plan metadata:** docs commit follows this SUMMARY.

## Pinned actions

| Action | Tag | SHA |
|---|---|---|
| actions/checkout | v7.0.1 | 3d3c42e5aac5ba805825da76410c181273ba90b1 |
| astral-sh/setup-uv | v10.3.3 | 68559e99cc807c1eb7e9238fd43a15bba460eec2 |
| actions/setup-node | v7.1.0 | 949feb2413d6458794dcd2491c4babbbce0c15c1 |
| actions/setup-java | v6.1.0 | b843ebf9b913146b38da2eaa7aeddf76074ae1ad |
| gradle/actions (setup-gradle) | v6.4.1 | 8da46b539cd8fe6ab27ca75128919a18d757604c |

## Files Created/Modified
- `.github/workflows/ci.yml` - per-PR CI: backend, dashboard, mobile jobs
- `.github/workflows/ios-nightly.yml` - nightly/manual iOS simulator tests
- `backend/core/tests/test_smoke.py` - TypeVar-generic `_cb_roundtrip` / `_mongo_roundtrip`
- `backend/api/tests/test_session_store.py` - `FUTURE` fixed to 2099-01-01 UTC (mongomock TTL sweeps by wall clock)

## Decisions Made
- Node 22 for the dashboard job (see key-decisions).
- No other test in the api suite depended on wall-clock TTL; the full suite is green after the single change.

## Deviations from Plan

None - plan executed exactly as written. (Process note: the first attempt halted because HEAD was on protected `main`; the user chose a phase branch and the plan resumed unchanged.)

## Issues Encountered
- Commit guard refused `main`; resolved by the orchestrator creating `gsd/phase-01-foundations-architecture-decisions`.

## Known open checks (gate merge of the CI PR)
- **Mobile job: known-open.** `./gradlew testAndroidHostTest` has not run anywhere; the planning machine has no JDK or Android SDK. First run is the Mobile job on the CI PR. If AGP cannot find compileSdk 36, add an `sdkmanager "platforms;android-36"` step. Mobile run URL: pending.
- **PR human-check pending (user approval needed to push and open a PR):** run `gh pr checks --watch`, require Backend, Dashboard and Mobile green, then push a throwaway commit breaking one backend test, confirm Backend turns red while Dashboard and Mobile still report, and revert it. Optionally mark the three checks required in branch protection.
- **iOS nightly:** after merge, `gh workflow run ios-nightly.yml` and confirm green.

## User Setup Required
None - no external service configuration required.

## Threat Flags
None. No secrets referenced, unprivileged `pull_request` trigger only, all actions SHA-pinned.

## Next Phase Readiness
CI is defined and green locally for backend and dashboard. Merge of the CI PR waits on the first green Mobile run.

## Self-Check: PASSED
- Files exist: ci.yml, ios-nightly.yml, both test files.
- Commits 205c6cb, b0d2af1, 6f63234 on the phase branch.
- Acceptance greps re-run: pyright 0 errors, api 0 failed, `type: ignore` count 1, 0 `pull_request_target`, 0 `secrets.`, 5 sync-gated steps, YAML assertion scripts print ok.
