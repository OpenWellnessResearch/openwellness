---
phase: "02"
slug: "route-authentication-authorization"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-04"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8 + FastAPI TestClient (api); Vitest 4.1 (dashboard); kotlin-test + MockEngine (mobile) |
| **Config file** | `backend/api/pyproject.toml` dev extra; `backend/api/tests/conftest.py` |
| **Quick run command** | `cd backend/api && uv run --frozen pytest -q -x tests/test_route_enumeration.py tests/test_policy_matrix.py tests/test_adr_policy_table.py` |
| **Full suite command** | `cd backend && uv sync --frozen --extra dev && (cd core && uv run --frozen pytest -q) && (cd api && uv run --frozen pytest -q) && (cd scheduler && uv run --frozen pytest -q) && uv run --frozen pyright` |
| **Estimated runtime** | ~30 seconds (baseline api 232 tests in 23.5 s, core 88 in 0.4 s) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched area
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite, dashboard `npm test` (Node 22), Kotlin `testAndroidHostTest` (CI) green; manual UAT signed
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (filled by planner / validate-phase) | — | — | AUTH-01 | — | Anonymous request to any non-exempt route is 401; flag and header gone | integration + source invariant | `pytest tests/test_route_enumeration.py tests/test_source_invariants.py -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-02 | — | Every route carries a valid `authorize(module, op)`; POLICY equals ADR 0007 | integration + unit | `pytest tests/test_route_enumeration.py tests/test_adr_policy_table.py -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-03 | — | Other user's resources 404, including through `filter=` | parametrized integration | `pytest tests/test_policy_matrix.py -k owner -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-04 | — | Non-admin 403 on admin resources and user list | parametrized | `pytest tests/test_policy_matrix.py -k admin -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-05 | — | Coach limited to claimed studies; other study 404 | parametrized | `pytest tests/test_policy_matrix.py -k coach -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-06 | — | Forged `X-Principal-Id` ignored; `updated_by` equals `sub`; patch cannot move owner or study | integration | `pytest tests/test_audit_and_mass_assignment.py -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-09 | — | Sign-in, call, refresh, call, sign-out per role | integration flow | `pytest tests/test_e2e_roles_flow.py -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | AUTH-09 | — | Mobile gate rejects null participant before token save | Kotlin host test | `cd frontend/mobile && ./gradlew testAndroidHostTest` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/api/tests/conftest.py` — `create_app`-based app fixture, token helper, world fixture, fakes for all 36 providers
- [ ] `backend/api/tests/test_route_enumeration.py`, `test_policy_matrix.py`, `test_audit_and_mass_assignment.py`, `test_docs_gating.py`, `test_e2e_roles_flow.py`
- [ ] Migrate anonymous-client suites to real tokens; delete `enforce_principal` probe tests
- [ ] Mobile gate test and MockEngine bearer test (needs a JDK; CI has one)
- [ ] Framework install: none

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coach signs in and works in the dashboard; participant signs in on Android and iOS simulator, against a live API | AUTH-09 | Needs live stores, an SMTP sink and simulators (D-12, D-13) | UAT checklist in the phase directory, using the D-04 seed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
