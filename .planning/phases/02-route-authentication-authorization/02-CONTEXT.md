# Phase 2: Route Authentication & Authorization - Context

**Gathered:** 2026-11-04
**Status:** Ready for planning

<domain>
## Phase Boundary

No participant health data is reachable without a verified token, and every caller reaches only what their identity and role allow:
- Deny-by-default bearer auth on every `/v1` route except `/v1/auth:*`; `enforce_principal` removed; a test enumerates every route — AUTH-01, AUTH-02
- Owner binding, including through `filter=` — AUTH-03
- Admin role gates and study-scoped coach access, implementing the ADR 0007 table — AUTH-04, AUTH-05
- Audit fields only from the verified token; `X-Principal-Id` ignored — AUTH-06
- Dashboard and mobile keep working end to end against the enforced API — AUTH-09

The policy itself is already decided in ADRs 0005, 0006 and 0007 and is not reopened here. Asymmetric signing, JWKS and the refresh grace window are Phase 3. The real bootstrap CLI is Phase 11.

</domain>

<decisions>
## Implementation Decisions

Numbers below are this phase's. ADRs cite Phase 1's numbering, so an ADR's "D-02" means Phase 1 D-02 (study-scoped coaches), not the D-02 here.

### Staff sign-in
- **D-01:** Login eligibility becomes: active, and either a participant (`roles.participant.pid` present and `verified_id` truthy) or a coach/admin role. Applies to both `_eligible_login_user` and `verify_login_code`. Users with no usable role stay locked out, and the uniform anti-enumeration responses do not change.
- **D-02:** Each client admits only its own audience. The dashboard role gate stays as it is (participants stay out, `useLogin.ts`, `AuthContext.tsx`). Mobile adds a matching gate that rejects accounts with no participant. These gates are UX only; the API's route enforcement is the security boundary, and no client-identifying wire change is made.
- **D-03:** `verified_id` is waived for coach/admin. An admin created the account, and the OTP proves mailbox control at each login. `verified_id` keeps its meaning for participants. No staff registration flow.
- **D-04:** A small dev seed script creates one admin, one coach, one participant and the study linking them, through the repository ports, for local work and the Phase 2 UAT. It is not documented for production, and Phase 11's `bootstrap` replaces it. No pre-auth setup endpoint.
- **D-05:** A coach with an empty study list can log in and matches no data.

### Denial edge cases
- **D-06:** Scope is evaluated before role. Out of scope is 404 for any method, and 403 appears only within the caller's own scope or on routes with no scope, such as `/v1/admins`. Example: a participant's `POST /v1/users/{someone-else}/conditions` is 404; the same request under their own id is 403.
- **D-07:** A multi-role caller gets the union of their cells, each cell still under its own predicate. A coach who is also a participant has self rights on their own data and coach rights in their studies.
- **D-08:** Coach list on an owner-scoped route: filter by each record's `study_id`, scope first and before `filter=`. If the scope filter removed records and none remain, answer 404. Otherwise answer 200, which may be empty, so an in-study participant with no data gets an empty list and records from a past study stay visible to that study's coach. No Participant read on list. **Accepted risk:** a signed-in coach can tell whether an out-of-study id has records in the requested range (404 vs empty 200), without seeing them. Accepted because only an authenticated, admin-assigned coach can probe it.
- **D-09:** `/docs`, `/redoc` and `/openapi.json` are off unless one setting enables them, default off. `.env.example` enables them for local development. With the setting off, the enumeration test allows no anonymous routes beyond ADR 0007's two.

### End-to-end proof
- **D-10:** The roadmap's logging-only pass is replaced by a static check: a recorded grep of dashboard and mobile call sites as evidence (scouting found only `auth:*`). Enforcement lands in one step, permissive mode is deleted with `enforce_principal`, and the Phase 2 roadmap research flag is updated to say why.
- **D-11:** "End to end" proves each client's sign-in, session restore, refresh and sign-out, plus one authorized resource call per role made the way a client would. No new screens.
- **D-12:** The proof runs twice over: a pytest flow on in-memory fakes in CI on every PR, plus one written manual UAT with the real clients against a live local API using the D-04 seed.
- **D-13:** UAT targets are the dashboard, Android and the iOS simulator. No physical devices, since server-URL configuration arrives in Phase 8.

### Policy wiring & audit
- **D-14:** One central Python table holds the policy, one row per resource laid out like ADR 0007, keyed by module and operation. Anything missing is denied. Routers supply their operation and record. No generic router factory. — **Reversibility:** costly — every router and policy test binds to this shape.
- **D-15:** A test parses the ADR 0007 markdown table and asserts every cell matches the Python table; behavior tests are parametrized from the Python table. Extend the row parsing in `backend/api/tests/test_adr_policy_table.py`. The API never reads the ADR at runtime.
- **D-16:** `updated_by` and other audit fields always record `sub` (user id), for every caller. Rows written earlier may hold a participant id. — **Reversibility:** costly — rows written from now on hold user ids, and Phase 11's audit actor is expected to match.

### Claude's Discretion
- The docs setting's name, under the existing `API_` prefix.
- Seed script location and invocation, within D-04.
- The error mobile shows for the D-02 gate (the dashboard's `NotAuthorized` is the model).
- How deny-by-default attaches at the router, how routers declare their operation, and how the test client obtains tokens.
- Whether scope filtering lives in API helpers or new port methods, provided scope applies before `filter=` and pagination stays correct.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authorization policy (the contract this phase implements)
- `docs/adr/0007-authorization-policy-table.md` — 36-row policy table, scope predicates, write rules, Fitbit response filter, mass-assignment caveat
- `docs/adr/0006-coach-study-scope.md` — `roles.coach.studies`, the `coach_studies` claim, 930 s staleness
- `docs/adr/0005-owner-semantics.md` — `owner` is the participant id, separate `{user}` bindings, exceptions
- `docs/adr/0004-access-token-format.md` — claims; signing change itself is Phase 3
- `docs/adr/0003-soft-delete-archive-purge.md` — archive, undelete and purge semantics

### Planning
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, research flag (superseded on the logging pass by D-10)
- `.planning/REQUIREMENTS.md` — AUTH-01..06, AUTH-09
- `.planning/PROJECT.md` — constraints: wire contract stable, tests without live infrastructure
- `.planning/STATE.md` — open blockers: duplicate-email oracle and Fitbit tokens must close in this phase

### Research
- `.planning/research/PITFALLS.md` — Pitfall 2 (owner-binding IDOR), Pitfall 3 (auth rollout breaking clients)
- `.planning/codebase/CONCERNS.md` — unauthenticated routes, dead `require_principal`
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/api/src/openwellness_api/deps/principal.py`: `Principal`, `get_principal` (never raises; must stop falling back to `X-Principal-Id`), `require_principal` (permissive mode to delete).
- `backend/api/src/openwellness_api/auth/token_service.py`: `AccessClaims` and `mint_access` need `coach_studies` added; claim-shape validation pattern already there.
- `backend/api/src/openwellness_api/auth/service.py`: `_roles_list`, `_participant_pid`, `_eligible_login_user`, `verify_login_code`, `_issue_credential`.
- `backend/api/src/openwellness_api/common/handlers.py`: `check_parent`, `stamp_audit`, `apply_patch`, `not_found`, the natural enforcement seams.
- `backend/api/tests/test_adr_policy_table.py`: existing ADR row parser.
- `frontend/dashboard/src/core/auth/jwt.ts`: `hasCoachOrAdminRole`, the model for the mobile gate.

### Established Patterns
- 36 routers built by `build_router()` and registered through `RESOURCE_MODULES`; `v1.py` aggregates them and includes auth separately, so deny-by-default must not catch `auth:*`.
- Lists fetch then paginate in memory (`get_for_owner_between`, then `paginate`, in `resources/weight.py`), so a scope filter fits between the two. Hand-rolled modules (`participant`, `goal`) diverge from the skeleton.
- Denials use `build_error` and `not_found`; AIP-193 envelope stays stable.

### Integration Points
- `backend/api/src/openwellness_api/main.py`: `FastAPI(...)` is where the docs URLs get gated (D-09).
- `backend/api/src/openwellness_api/config.py`: remove `enforce_principal`; add the docs setting.
- `backend/api/tests/conftest.py` and suites sending `X-Principal-Id` (`test_weights_owner_crud.py`, `test_goals_carveout.py`, `test_principal.py`, `test_auth_api.py`): must move to real tokens.
- `backend/api/README.md`: documents `X-Principal-Id` and must be corrected.
- `frontend/mobile/feature/auth/`: the mobile gate (D-02); `participant` is already nullable in `AuthModels.kt`.

### Must verify in research
- The refresh path was not read during discussion: confirm `refresh_token` and `_issue_credential` accept a staff user with a null participant, and apply D-01 consistently there.
- ADR 0007 says `POST /v1/users` is admin-only, and `UserCreate` accepts `roles`; confirm patch allowlists per the mass-assignment caveat.

</code_context>

<specifics>
## Specific Ideas

- Participants must never log in to the dashboard, and must be able to log in to the app (developer, during discussion).
- D-06, D-07, D-08 and D-09 go beyond what ADR 0007 states. Record them as an amendment to ADR 0007 so the policy document stays the single written contract.
- `.env.example` is also the template copied onto VMs, so D-09's local default could turn docs on in a deployment. Phase 12's guide and Phase 10's env work must set it off explicitly for production.

</specifics>

<deferred>
## Deferred Ideas

- Trusted-proxy handling of `X-Forwarded-For`: `_client_ip` trusts the first hop today. In the research notes, but no AUTH-* requirement covers it. Noted for Phase 12.
- Redacted structured logging: in the research notes, no requirement. Backlog.
- `kid` and JWKS groundwork: Phase 3.
- Real bootstrap CLI with `--demo`: Phase 11 (KIT-06), replacing the D-04 seed.
- Running the UAT on physical devices: after Phase 8's server-URL configuration.

</deferred>

---

*Phase: 02-route-authentication-authorization*
*Context gathered: 2026-11-04*
