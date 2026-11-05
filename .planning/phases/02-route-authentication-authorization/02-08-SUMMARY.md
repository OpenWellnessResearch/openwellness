---
phase: 02-route-authentication-authorization
plan: 08
subsystem: auth
tags: [authorization, policy-engine, admin-only, duplicate-email-oracle, auth-04]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: authorize/Access engine, weight reference router, policy matrix harness (plan 02-04)
provides:
  - user, admin and app routers with every handler behind authorize
  - POST /v1/users is admin-only, so the duplicate-email 409 cannot be reached by a non-admin
  - AdminUserBody that validates a stored AdminUser (admin responses no longer 400)
  - tests/test_admin_rows.py
affects: [02-10 route structure test and wave-boundary full run, 02-12 records the closed blocker]

actuals:
  tokens: 4900
  tasks: 2
  commits: 4

commits: 4
plan_head_before: 60341476b3782ff55dca7456cb65c24ada86fd9a
plan_head_after: 8bdcb234c1001fdf68668d0f5f607ff31d092513

tech-stack:
  added: []
  patterns:
    - "Admin-only rows: authorize runs before the handler, so a handler-level check (duplicate email) is unreachable for a non-admin"
    - "SCHEMA_CONFIG | ConfigDict(from_attributes=True) to extend the shared wire config for one model"

key-files:
  created:
    - backend/api/tests/test_admin_rows.py
  modified:
    - backend/api/src/openwellness_api/resources/user.py
    - backend/api/src/openwellness_api/resources/admin.py
    - backend/api/src/openwellness_api/resources/app.py
    - backend/api/src/openwellness_api/schemas/admin.py

key-decisions:
  - "Duplicate-email oracle closed by the policy cell, not by changing the 409 handler: POST /v1/users is admin-only, and authorize runs before the handler"
  - "AdminUserBody extends SCHEMA_CONFIG with `SCHEMA_CONFIG | ConfigDict(from_attributes=True)` instead of the plan's `ConfigDict(**SCHEMA_CONFIG, from_attributes=True)`, which pyright rejects"

requirements-completed: [AUTH-04, AUTH-06]

coverage:
  - id: D1
    description: "Non-admins get 403 on /v1/admins, /v1/apps and GET /v1/users; admins get the full cell"
    requirement: AUTH-04
    verification:
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_non_admin_403_on_admin_resources"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_non_admin_403_on_user_list"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_policy_matrix[user-/admin-/app-]"
        status: pass
    human_judgment: false
  - id: D2
    description: "Role comparison is exact, an empty roles list has no admin column, and role order does not matter"
    requirement: AUTH-04
    verification:
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_role_match_is_exact"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_empty_roles_is_403"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_role_order_is_irrelevant"
        status: pass
    human_judgment: false
  - id: D3
    description: "Duplicate-email oracle closed: coach, participant and no-role callers get 403 on POST /v1/users before any duplicate check; only an admin sees 409"
    requirement: AUTH-04
    verification:
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_duplicate_email_is_403_for_non_admin"
        status: pass
    human_judgment: false
  - id: D4
    description: "A caller reads their own User by sub, another user is 404, and roles change only through an admin patch"
    requirement: AUTH-06
    verification:
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_self_user_binds_to_sub"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_admin_patch_can_edit_roles"
        status: pass
    human_judgment: false
  - id: D5
    description: "Admins can create and read /v1/admins with the nested user object in the response"
    requirement: AUTH-04
    verification:
      - kind: integration
        ref: "backend/api/tests/test_admin_rows.py#test_admin_round_trip"
        status: pass
    human_judgment: false

duration: about 15 min
completed: 2026-11-04
---

# Phase 2 Plan 08: Admin-only routers and the closed duplicate-email oracle Summary

**`user`, `admin` and `app` now run every handler through the policy engine, so a non-admin gets 403 on `POST /v1/users` before the duplicate-email 409 can fire, and `/v1/admins` responses serialize for admins for the first time.**

## Accomplishments

- `user.py`: `authorize("user", op)` on all seven ops, `check_record` at the end of `_fetch`, `scope_list` on list, `apply_patch(..., principal=access.principal)`. A caller reads their own record by `sub` (404 for another user's), cannot patch it (403), and `roles` change only through an admin patch (the `_ADMIN_ONLY_PATCH_FIELDS` filter from plan 02-04 backs that up).
- `admin.py`, `app.py`: same recipe with modules `admin` and `app`. `admin.py` keeps its own patch loop, as planned.
- `schemas/admin.py`: `AdminUserBody` reads from attributes, so the stored `AdminUser` dataclass validates (assumption A-08-1). Before this, every admin response was a 400.
- `tests/test_admin_rows.py`: 18 tests (parametrized from the 9 planned behaviors).

## TDD Gate Compliance

Task 1: RED `f3f1d4e` (6 of 7 failed on the planned status assertions: 200 vs 403 on list, create and roles patch, and self-user bindings; no collection or import errors), GREEN `7801a7c`. Tracer gate: `<verify>` re-run gave 23 passed and 49 matrix passed; verified end-to-end, expanded.
Task 2: RED `4a61f64` (10 failed: 403 expected for non-admins and exact-role tokens, and the 400 on the admin round trip; the role-order and admin-list cases pass beforehand by design, since no gate means everything is allowed), GREEN `8bdcb23`. No REFACTOR commits. `gsd_run check tdd-red-evidence` was not run (plan `type: execute`, `workflow.tdd_mode` not enabled); RED was judged from the pytest report.

## Deviations from Plan

**1. [Rule 3 - Blocking] `AdminUserBody` config form** - Found during: Task 2 verification (pyright). The plan's `ConfigDict(**SCHEMA_CONFIG, from_attributes=True)` reports 2 pyright errors ("already assigned"), though it runs. Used `SCHEMA_CONFIG | ConfigDict(from_attributes=True)`, which is equivalent at runtime and clean under pyright. Files: `schemas/admin.py`. Commit: `8bdcb23`.

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none on behavior.

## Known Stubs

None.

## Issues Encountered

- The `create` handler in each router takes `access` only to run `authorize`; the parameter is otherwise unused (the three rows have no binding, so no `stamp_create`), as the plan specifies.

## Threat Flags

None. T-02-17 (duplicate-email oracle) and T-02-35 (roles mass assignment) are covered by `test_duplicate_email_is_403_for_non_admin`, `test_admin_patch_can_edit_roles` and `test_self_user_binds_to_sub`. The auth routes (`/v1/auth:*`) are untouched and keep their uniform responses.

## Verification

- Plan scoped checks: `tests/test_admin_rows.py tests/test_users_crud.py tests/test_repository_errors.py` 35 passed; matrix `-k "[user- or [admin- or [app-"` 147 passed (49 + 98).
- Per suite: api 1986 passed (1821 before), core 88 passed, scheduler 4 passed. Pyright on the four touched source files: 0 errors.
- All three modules are in `ROLLED_OUT`, so the matrix confirms every handler goes through the engine.

## Self-Check: PASSED

- FOUND: backend/api/tests/test_admin_rows.py
- FOUND: backend/api/src/openwellness_api/resources/user.py, admin.py, app.py; backend/api/src/openwellness_api/schemas/admin.py
- FOUND commits: f3f1d4e, 7801a7c, 4a61f64, 8bdcb23
