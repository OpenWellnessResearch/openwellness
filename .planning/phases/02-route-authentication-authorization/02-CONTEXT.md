# Phase 2: Route Authentication & Authorization - Context

**Gathered:** 2026-11-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Every `/v1` route except `/v1/auth:*` and `/healthz` rejects anonymous callers with 401, and one policy layer enforces the ADR 0007 table per resource and method: owner binding (ADR 0005), study-scoped coach access through the `coach_studies` claim (ADR 0006), the study-binding write rules, and audit identity taken only from the verified token. Requirements AUTH-01 through AUTH-06 and AUTH-09.

What this phase does **not** do: asymmetric token signing, `kid` and JWKS (AUTH-07, Phase 3); refresh grace window (AUTH-08, Phase 3); Postgres (Phase 4); sync rules (Phase 6); new data screens in the dashboard or mobile app.

The WHAT is locked by Phase 1's ADRs. This context records only HOW to implement it.

</domain>

<decisions>
## Implementation Decisions

### Policy engine shape
- **D-01:** One shared `authorize(resource, method)` dependency factory under `backend/api/src/openwellness_api/deps/` (or a new `authz/` package) is the only source of 401 and 403. Each `build_router` attaches it to each route. An enumeration test walks `app.routes` and fails on any `/v1` route without it (allowlist: `/v1/auth:*`, `/healthz`). — **Reversibility:** costly — ~260 route declarations across 36 routers and the enumeration test encode it.
- **D-02:** The runtime source of truth is a typed Python policy module (e.g. `openwellness_api/authz/policy.py`): resource module name → caller column → allowed methods and scope predicate name, mirroring ADR 0007 cell for cell. A conformance test parses the ADR 0007 markdown table and asserts equality, extending `backend/api/tests/test_adr_policy_table.py`. Runtime never reads markdown. — **Reversibility:** reversible — the ADR stays the human document; the module can be regenerated from it.
- **D-03:** Routes declare resource and method explicitly, e.g. `Depends(authorize("weight", "patch"))`, never inferred from HTTP verb and path. Custom methods (`studies:lookup`, `conversations:search`) get explicit declarations too, matching the ADR 0007 custom-methods table.
- **D-04:** Split of work: the dependency verifies the bearer, checks the caller's role column, and returns the resolved scope rule for the cell. The handler applies the scope rule after its existing fetch through a shared `check_scope(entity, principal, rule)` helper that replaces today's `check_parent` in `common/handlers.py`. One fetch per request; the helper is unit-testable per predicate.

### Scope filtering for lists
- **D-05:** For Phase 2, list scope (`self-owner`, `coach-study`, membership) is applied as an in-memory post-filter at the API layer on the result of the existing port query. No new repository port methods and no Couchbase or Mongo adapter changes. — **Reversibility:** reversible — Phase 4's Postgres adapters push scope into SQL and the post-filter becomes a no-op; nothing outside the API layer depends on it.
- **D-06:** Membership rows use the same post-filter: `participant_group` keeps rows whose `participant_ids` contains the participant claim; `conversation` keeps rows whose `channels` contains `participantGroup:{id}` for a non-archived group the caller is a member of (one extra group query per request).
- **D-07:** `filter=` rejects scope fields. `owner` and `study_id` are removed from every router's `allowed_fields` map, so `filter=owner=other` returns 400 INVALID_ARGUMENT like any unknown field. The hostile-filter test is one parametrized case per resource. — **Reversibility:** reversible — narrows the `filter=` surface; no client uses those fields today.
- **D-08:** List pipeline order: fetch → scope rule → parsed `filter=` → offset slice. Page tokens stay stable because the slice sees the filtered list. The admin column is global (D-04 of Phase 1): its scope rule is a no-op and admin lists are unchanged from today.

### Rollout and flag removal
- **D-09:** Enforce directly in one change and delete `AuthSettings.enforce_principal`. No logging-only pass and no temporary toggle: the dashboard and mobile app call only `/v1/auth:*` today, so there is no unauthenticated data traffic to observe. — **Reversibility:** costly — once enforced, every client call must carry a bearer; relaxing it would mean re-adding a flag AUTH-01 forbids.
- **D-10:** `get_principal` and `require_principal` collapse into one strict dependency (working name `current_principal`) that raises 401 on any missing, malformed or expired bearer with no anonymous fallback. The `X-Principal-Id` `Header` parameter is deleted from the signature so a forged header is never read (AUTH-06). `Principal.id` stays the token `sub`; `stamp_audit` and `apply_patch` keep taking the `Principal`. — **Reversibility:** costly — 37 routers change their import; the header leaves the wire surface.
- **D-11:** Tests authenticate with real HS256 access tokens minted in `conftest.py` through the real token service and test secret, with fixtures for admin, coach (carrying `coach_studies`) and participant callers. Existing CRUD tests pick the fixture their route needs. No dependency overrides for the principal.
- **D-12:** Policy coverage is a generated matrix test: one parametrized test for anonymous 401 across `app.routes`, and one that generates a case per (resource, caller, method) from the policy module expecting success, 403 or 404. It is backed by a per-resource fixture table (one in-scope record, one out-of-scope record, one valid create body) over the existing repository fakes, roughly 36 entries.

### First admin and bootstrap
- **D-13:** OTP login eligibility drops the participant-id requirement: a user is eligible when active, verified (`verified_id` set) and holding at least one role. Both `_eligible_login_user` and `verify_login_code` in `auth/service.py` change. The `participant` claim is minted only when the participant role is present; `coach_studies` only for coaches (from `roles.coach.studies`, ADR 0006). Registration still requires a participant. — **Reversibility:** costly — auth flows, claims minting and their tests change; the dashboard relies on coach login working.
- **D-14:** A small CLI in the api package, e.g. `uv run python -m openwellness_api.bootstrap --email <addr> [--coach-studies ...]`, creates or updates a user with the admin role and a verified marker through the `UserRepository` port, so it works on Mongo now and Postgres later. Phase 10's seed command wraps it.
- **D-15:** Admins assign coach studies through the existing `PATCH /v1/users/{user}`, which the policy table already makes admin-only. The user update schema refuses `roles` from any non-admin body (mass-assignment guard from ADR 0007), so a future self-service patch can never touch roles. No new custom method.
- **D-16:** AUTH-09 is proven by automated API flow tests (bootstrap admin → admin creates study, participant and coach → coach lists in-scope participants and gets 404 elsewhere → participant reads own weights, with real OTP and tokens over the fakes) plus two manual UAT items: coach OTP login in the dashboard and participant OTP login in the mobile app against a running enforced API.

### Consequences the planner must carry
- The duplicate-email oracle on `POST /v1/users` (Phase 1 accepted gap, STATE.md blocker) closes automatically: the `user` create cell is admin-only.
- The Fitbit `access_token` and `refresh_token` must be returned as null to non-admin callers (ADR 0007 `fitbit` row); implementation placement is Claude's discretion.
- Removing `enforce_principal` also removes it from `.env.example` and the README; `AUTH_*` docs must not reference it.

### Claude's Discretion
- Exact module and function names (`authz/policy.py`, `current_principal`, `check_scope`, the CLI module), as long as D-01 to D-04 hold.
- Where the Fitbit token redaction lives (serializer, router, or schema) provided non-admin responses carry null tokens and the `/v1` shape is unchanged.
- How the `self-study` predicate reads the caller's Participant record per request (helper on the dependency vs. handler) and how the result is cached within one request.
- Error envelope details for 403 beyond `build_error(403, "PERMISSION_DENIED", ...)`.
- Shape of the per-resource fixture table for the matrix test.
- Whether the `coach_studies` claim is an empty list or absent for non-coaches (ADR 0006 allows either; the policy must treat both as matching nothing).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authorization contract (locked in Phase 1)
- `docs/adr/0007-authorization-policy-table.md` — the 36-row policy table, custom-methods table, scope predicates, study-binding write rules, denial codes; Phase 2 implements it mechanically
- `docs/adr/0006-coach-study-scope.md` — `roles.coach.studies` storage, `coach_studies` claim, 930 s staleness window, admin-only edits
- `docs/adr/0005-owner-semantics.md` — `owner` holds the participant id; `{user}` binds to `participant` on sub-resources and to `sub` on the User resource; membership exceptions
- `docs/adr/0004-access-token-format.md` — claim set (`sub`, `participant`, `roles`, `aud`); HS256 stays until Phase 3
- `docs/adr/0003-soft-delete-archive-purge.md` — purge is admin-only hard delete

### Planning
- `.planning/ROADMAP.md` — Phase 2 goal, five success criteria, research flag
- `.planning/REQUIREMENTS.md` — AUTH-01 … AUTH-06, AUTH-09 (AUTH-07, AUTH-08 are Phase 3)
- `.planning/phases/01-foundations-architecture-decisions/01-CONTEXT.md` — D-01 … D-06 on authorization, D-13 on tokens
- `.planning/phases/01-foundations-architecture-decisions/01-SECURITY.md` — threats T-01-23 … T-01-29, T-01-32, T-01-33 carried into this phase
- `.planning/codebase/CONCERNS.md` — "Resource routes never authenticate", "`X-Principal-Id` header is trusted", "No authorization model"

### Code the plans touch
- `backend/api/src/openwellness_api/deps/principal.py` — the two dependencies and header to collapse (D-10)
- `backend/api/src/openwellness_api/common/handlers.py` — `check_parent`, `stamp_audit`, `apply_patch` (D-04)
- `backend/api/src/openwellness_api/common/filter.py` — `parse_filter` and `allowed_fields` (D-07)
- `backend/api/src/openwellness_api/common/pagination.py` — offset slicing (D-08)
- `backend/api/src/openwellness_api/auth/service.py` — `_eligible_login_user`, `verify_login_code`, `_issue_credential` (D-13)
- `backend/api/src/openwellness_api/auth/token_service.py` — `AccessClaims`, `issue`/`verify_access` (new `coach_studies` claim)
- `backend/api/src/openwellness_api/config.py` — `AuthSettings.enforce_principal` to delete (D-09)
- `backend/api/src/openwellness_api/resources/__init__.py`, `v1.py`, `resources/weight.py` — router skeleton every resource follows
- `backend/api/tests/test_adr_policy_table.py`, `backend/api/tests/conftest.py` — conformance test to extend, fixtures to add (D-02, D-11)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Principal` dataclass (`deps/principal.py`): already carries `roles` and `participant` from verified claims; gains `coach_studies`.
- `check_parent` / `not_found` (`common/handlers.py`): the 404 anti-enumeration helpers; `check_scope` generalizes `check_parent` from "owner equals segment" to the ADR 0007 predicates.
- `parse_filter` with per-router `allowed_fields`: the single place to drop scope fields (D-07).
- `JwtTokenService.issue` / `verify_access`: claim validation already rejects malformed `roles` and `participant`; add `coach_studies` with the same shape checks.
- Test fakes: mongomock, fakeredis, time-machine and the recording `UserRepository` fake used by `test_auth_service.py`; `test_users_crud.py` and `test_weights_owner_crud.py` are the CRUD suites to re-point at role fixtures.
- Dashboard `AuthContext` already exposes `roles` and gates coach and admin; the Ktor client already attaches bearers and refreshes on 401.

### Established Patterns
- Every router is `build_router()` with `container_dep("<repo>")`, `Depends(get_principal)` only for audit stamping, and AIP errors via `build_error`; 37 modules share the skeleton, so the swap to `authorize(...)` plus `current_principal` is mechanical.
- Anti-enumeration: wrong owner is 404 via `EntityNotFoundException`; auth responses are uniform. 403 is new and must use `build_error(403, "PERMISSION_DENIED", ...)`.
- Lists materialize the full result then slice by opaque offset token; post-filtering before the slice preserves tokens.
- Clocks and settings are injected; `AuthSettings` is read off `app.state.auth_container`.

### Integration Points
- `v1.py` mounts every `RESOURCE_MODULES` router plus the auth router; the enumeration test reads `app.routes` from `create_app()`.
- `main.py` lifespan wires `auth_container`; the strict dependency resolves the token service from it.
- `auth/service.py` mints claims at login and refresh (`_issue_credential`); `coach_studies` is read from `user.roles["coach"]["studies"]` there.
- `schemas/user.py` carries `roles`; the mass-assignment guard (D-15) lives in the update schema or the user router.
- `.env.example` and `backend/README.md` list `API_AUTH_*`; `enforce_principal` disappears from both.

</code_context>

<specifics>
## Specific Ideas

- The enumeration test and the matrix test are the proof the phase is done; the planner should make them Wave 0 (red first) and let the policy module and dependency turn them green.
- Resource names in `authorize(...)` are the `RESOURCE_MODULES` module names so the ADR conformance test, the policy module and the route declarations share one vocabulary.
- The bootstrap CLI is the first step of the AUTH-09 flow test, so it is built before the flow test, not after.
- The 01-SECURITY.md register carries forward T-01-21 (HS256 still live) and T-01-28 (hostile-filter test owed here); the hostile-filter test satisfies T-01-28.

</specifics>

<deferred>
## Deferred Ideas

- Port-level scope queries (list-by-study-ids, membership queries) — Phase 4 Postgres adapters implement scope in SQL (D-05).
- Data screens in the dashboard and mobile app that exercise bearer-carrying data calls — mobile and dashboard phases; Phase 2 proves AUTH-09 with API flow tests plus manual login UAT.
- A dedicated `users/{user}:setCoachStudies` custom method — not needed while the admin-only user patch carries roles (D-15).
- A separate staff login endpoint — rejected in favor of one OTP flow (D-13).
- A temporary log-only enforcement toggle — rejected (D-09).
- Postgres row-level security as defense in depth — v2 AUTHZ-02.
- `X-Forwarded-For` trust for rate limiting and the refresh token in dashboard `localStorage` — recorded in `.planning/codebase/CONCERNS.md`; belong to deployment hardening (Phase 12) and a dashboard phase, not route auth.

</deferred>

---

*Phase: 02-route-authentication-authorization*
*Context gathered: 2026-11-03*
