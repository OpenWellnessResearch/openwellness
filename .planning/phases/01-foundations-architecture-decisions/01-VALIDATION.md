---
phase: "01"
slug: "foundations-architecture-decisions"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-30"
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Reconstructed after execution by `/gsd-validate-phase 01` (State B: no VALIDATION.md existed, all 11 SUMMARYs did).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8 (backend, three packages), Vitest 4 (dashboard), Gradle KMP host tests (mobile) |
| **Config file** | none for pytest (defaults; each `tests/conftest.py` pins `OPENWELLNESS_ENV_FILE` to `os.devnull`); `backend/pyrightconfig.json`; `frontend/dashboard/vite.config.ts` |
| **Quick run command** | `cd backend/core && uv run --frozen pytest -q` then `cd backend/api && uv run --frozen pytest -q` |
| **Full suite command** | `.github/workflows/ci.yml` jobs: backend (`uv run --frozen pytest` per package, `uv run --frozen pyright`, `uv run --frozen python core/scripts/check_no_fstring_n1ql.py`), dashboard (`npm run lint`, `npm run typecheck`, `npm test`, `npm run format:check`), mobile (`./gradlew testAndroidHostTest --stacktrace`) |
| **Estimated runtime** | ~30 seconds backend locally; ~3 minutes full CI |

Note: the three backend packages must be run separately. A combined `pytest core api scheduler` fails on a duplicate `tests.conftest` module name.

---

## Sampling Rate

- **After every task commit:** Run `cd backend/core && uv run --frozen pytest -q && cd ../api && uv run --frozen pytest -q`
- **After every plan wave:** Run the full CI job set (push to a PR branch)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds locally, 180 seconds in CI

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01..03 | 01 | 1 | FOUND-01 | — | N/A | smoke (yaml) | `cd backend/core && uv run --frozen pytest -q tests/test_ci_workflow.py` | ✅ | ✅ green |
| 01-02-01..02 | 02 | 1 | FOUND-02, FOUND-03 | — | N/A | unit | `cd backend/core && uv run --frozen pytest -q tests/test_settings.py` and `cd backend/api && uv run --frozen pytest -q tests/test_settings_env.py` | ✅ | ✅ green |
| 01-03-01..02 | 03 | 1 | FOUND-06 | — | Outages surface as logged 500, never empty results | unit | `cd backend/api && uv run --frozen pytest -q tests/test_repository_errors.py tests/test_error_mapping.py` | ✅ | ✅ green |
| 01-04-01..02 | 04 | 2 | FOUND-04 | — | N/A | unit (ast) | `cd backend/api && uv run --frozen pytest -q tests/test_participant_ids.py` and `cd backend/core && uv run --frozen pytest -q tests/test_layering.py` | ✅ | ✅ green |
| 01-05-01..03 | 05 | 3 | FOUND-05, FOUND-06 | — | Anti-enumeration responses stay uniform | unit | `cd backend/api && uv run --frozen pytest -q tests/test_auth_service.py tests/test_auth_api.py tests/test_users_crud.py tests/test_source_invariants.py` | ✅ | ✅ green |
| 01-06-01..02 | 06 | 4 | FOUND-05 | — | Refresh rotation and reuse detection preserved over the port | contract | `cd backend/api && uv run --frozen pytest -q tests/test_refresh_session_repository.py` | ✅ | ✅ green |
| 01-07-01..03 | 07 | 1 | FOUND-07 | — | N/A | unit | `cd backend/api && uv run --frozen pytest -q tests/test_adr_policy_table.py` (ADR index) | ✅ | ✅ green |
| 01-08-01, 03 | 08 | 2 | FOUND-07 | — | N/A | unit | `cd backend/api && uv run --frozen pytest -q tests/test_adr_policy_table.py` | ✅ | ✅ green |
| 01-08-02 | 08 | 2 | FOUND-07 | — | N/A | manual | — (developer checkpoint on ADR content) | — | ✅ done in execution |
| 01-09-01..03 | 09 | 3 | FOUND-07 | — | Policy table covers every resource module | unit | `cd backend/api && uv run --frozen pytest -q tests/test_adr_policy_table.py` | ✅ | ✅ green |
| 01-10-01..02 | 10 | 2 | FOUND-03 | — | N/A | integration | `cd backend/core && uv run --frozen pytest -q tests/test_env_example.py` | ✅ | ✅ green |
| 01-11-01..02 | 11 | 5 | FOUND-05 | — | Session store wired through the port, collection name configurable | unit | `cd backend/api && uv run --frozen pytest -q tests/test_session_store.py tests/test_auth_container.py` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Discrepancy noted during audit: `01-08-SUMMARY.md` lists `requirements-completed: []` although its plan claims FOUND-07. FOUND-07 is ticked in REQUIREMENTS.md and covered by plans 01-07 and 01-09, so no requirement is orphaned.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The five tests below were added retroactively by the Nyquist audit (commit `b8cacd9`) to replace one-off grep and inline checks from plan verify blocks:

- [x] `backend/core/tests/test_layering.py` — FOUND-04 layering guard (no driver, framework, adapters or infrastructure imports in domain/ and application/)
- [x] `backend/api/tests/test_source_invariants.py` — FOUND-05, FOUND-06 (no pymongo/bson under api/src, no `print(` in src trees, no broad except in the Mongo base repository)
- [x] `backend/core/tests/test_env_example.py` — FOUND-03 (`.env.example` localhost values, compose Redis overrides)
- [x] `backend/core/tests/test_ci_workflow.py` — FOUND-01 (triggers, read-only permissions, SHA-pinned actions, three independent jobs, nightly iOS trigger set)
- [x] `backend/api/tests/test_adr_policy_table.py` — FOUND-07 (36 policy rows match `RESOURCE_MODULES`, ADR index lists 0001 through 0007)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A failing check is visible on a PR while the other jobs still report | FOUND-01 | Needs a live GitHub Actions run | Done 2026-10-30: throwaway draft PR #7 with one failing backend test; Backend red, Dashboard and Mobile green (run 41132076843). Recorded in 01-UAT.md. |
| ADR decisions are correct and complete | FOUND-07 | Decision content is prose; the test checks only structure and row coverage | Read docs/adr/0001 through 0007 against the Phase 2 and Postgres plans before relying on them |
| README documents the single repo-root `.env` | FOUND-03 | Wording check | Open backend/README.md and confirm the `.env` section matches `.env.example` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s locally
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-30

## Validation Audit 2026-10-30

| Metric | Count |
|---|---|
| Gaps found | 5 |
| Resolved | 5 |
| Escalated | 0 |
