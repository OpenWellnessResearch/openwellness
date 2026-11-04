# Phase 2: Route Authentication & Authorization - Research

**Researched:** 2026-11-04
**Domain:** FastAPI deny-by-default bearer auth, table-driven RBAC plus study-scoped ABAC over repository ports, OTP staff sign-in, client gates (React dashboard, Kotlin Multiplatform mobile)
**Confidence:** HIGH (everything is in-repo; no new libraries; the few runtime behaviors that mattered were probed in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Numbers below are this phase's. ADRs cite Phase 1's numbering, so an ADR's "D-02" means Phase 1 D-02 (study-scoped coaches), not the D-02 here.

#### Staff sign-in
- **D-01:** Login eligibility becomes: active, and either a participant (`roles.participant.pid` present and `verified_id` truthy) or a coach/admin role. Applies to both `_eligible_login_user` and `verify_login_code`. Users with no usable role stay locked out, and the uniform anti-enumeration responses do not change.
- **D-02:** Each client admits only its own audience. The dashboard role gate stays as it is (participants stay out, `useLogin.ts`, `AuthContext.tsx`). Mobile adds a matching gate that rejects accounts with no participant. These gates are UX only; the API's route enforcement is the security boundary, and no client-identifying wire change is made.
- **D-03:** `verified_id` is waived for coach/admin. An admin created the account, and the OTP proves mailbox control at each login. `verified_id` keeps its meaning for participants. No staff registration flow.
- **D-04:** A small dev seed script creates one admin, one coach, one participant and the study linking them, through the repository ports, for local work and the Phase 2 UAT. It is not documented for production, and Phase 11's `bootstrap` replaces it. No pre-auth setup endpoint.
- **D-05:** A coach with an empty study list can log in and matches no data.

#### Denial edge cases
- **D-06:** Scope is evaluated before role. Out of scope is 404 for any method, and 403 appears only within the caller's own scope or on routes with no scope, such as `/v1/admins`. Example: a participant's `POST /v1/users/{someone-else}/conditions` is 404; the same request under their own id is 403.
- **D-07:** A multi-role caller gets the union of their cells, each cell still under its own predicate. A coach who is also a participant has self rights on their own data and coach rights in their studies.
- **D-08:** Coach list on an owner-scoped route: filter by each record's `study_id`, scope first and before `filter=`. If the scope filter removed records and none remain, answer 404. Otherwise answer 200, which may be empty, so an in-study participant with no data gets an empty list and records from a past study stay visible to that study's coach. No Participant read on list. **Accepted risk:** a signed-in coach can tell whether an out-of-study id has records in the requested range (404 vs empty 200), without seeing them. Accepted because only an authenticated, admin-assigned coach can probe it.
- **D-09:** `/docs`, `/redoc` and `/openapi.json` are off unless one setting enables them, default off. `.env.example` enables them for local development. With the setting off, the enumeration test allows no anonymous routes beyond ADR 0007's two.

#### End-to-end proof
- **D-10:** The roadmap's logging-only pass is replaced by a static check: a recorded grep of dashboard and mobile call sites as evidence (scouting found only `auth:*`). Enforcement lands in one step, permissive mode is deleted with `enforce_principal`, and the Phase 2 roadmap research flag is updated to say why.
- **D-11:** "End to end" proves each client's sign-in, session restore, refresh and sign-out, plus one authorized resource call per role made the way a client would. No new screens.
- **D-12:** The proof runs twice over: a pytest flow on in-memory fakes in CI on every PR, plus one written manual UAT with the real clients against a live local API using the D-04 seed.
- **D-13:** UAT targets are the dashboard, Android and the iOS simulator. No physical devices, since server-URL configuration arrives in Phase 8.

#### Policy wiring & audit
- **D-14:** One central Python table holds the policy, one row per resource laid out like ADR 0007, keyed by module and operation. Anything missing is denied. Routers supply their operation and record. No generic router factory. — **Reversibility:** costly — every router and policy test binds to this shape.
- **D-15:** A test parses the ADR 0007 markdown table and asserts every cell matches the Python table; behavior tests are parametrized from the Python table. Extend the row parsing in `backend/api/tests/test_adr_policy_table.py`. The API never reads the ADR at runtime.
- **D-16:** `updated_by` and other audit fields always record `sub` (user id), for every caller. Rows written earlier may hold a participant id. — **Reversibility:** costly — rows written from now on hold user ids, and Phase 11's audit actor is expected to match.

### Claude's Discretion
- The docs setting's name, under the existing `API_` prefix.
- Seed script location and invocation, within D-04.
- The error mobile shows for the D-02 gate (the dashboard's `NotAuthorized` is the model).
- How deny-by-default attaches at the router, how routers declare their operation, and how the test client obtains tokens.
- Whether scope filtering lives in API helpers or new port methods, provided scope applies before `filter=` and pagination stays correct.

### Deferred Ideas (OUT OF SCOPE)
- Trusted-proxy handling of `X-Forwarded-For`: `_client_ip` trusts the first hop today. In the research notes, but no AUTH-* requirement covers it. Noted for Phase 12.
- Redacted structured logging: in the research notes, no requirement. Backlog.
- `kid` and JWKS groundwork: Phase 3.
- Real bootstrap CLI with `--demo`: Phase 11 (KIT-06), replacing the D-04 seed.
- Running the UAT on physical devices: after Phase 8's server-URL configuration.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Every `/v1` route except `/v1/auth:*` and `/healthz` rejects missing/invalid bearer with 401; `enforce_principal` removed | Router-level strict `get_principal` dependency in `v1.py` (probed: 401 precedes 422 for typed bodies); delete `enforce_principal`, `require_principal`, the `X-Principal-Id` fallback; docs gating (D-09) |
| AUTH-02 | A test enumerates every registered route and asserts anonymous gets 401 | `create_app` refactor so the test builds the real app; 265 routes today (253 `/v1` non-auth, 6 auth, healthz, 5 docs); structural test also checks each route carries `authorize(module, op)` |
| AUTH-03 | Participant reads/writes only under own `{user}`; other's resources 404 including via `filter=` | `self-owner` predicate in the policy engine; D-08 scope-then-filter; hostile-filter test; `filter=` grammar cannot name owner today (verified) |
| AUTH-04 | Admin resources and user list require admin (403) | Policy rows `admin`, `app`, `user`; D-06 rule: no-scope rows give 403 |
| AUTH-05 | Coach: role + `coach_studies` claim + owner's Participant study check on every write; other study is 404 | `coach_studies` claim (token_service, Principal, refresh re-mint), `coach-study` predicate, `study-binding` write rule, mass-assignment allowlist |
| AUTH-06 | Audit fields only from the token; `X-Principal-Id` ignored | Strict `get_principal` with no header read; `stamp_audit` assigns `sub` unconditionally; conversation create must start stamping |
| AUTH-09 | Dashboard and mobile keep working end to end | D-10 recorded grep (only `auth:*` calls exist); mobile gate before token persistence; pytest e2e flow; manual UAT with the D-04 seed |
</phase_requirements>

## Summary

All 253 non-auth `/v1` routes are anonymous today. `get_principal` degrades to a forgeable `X-Principal-Id` header, `require_principal` is dead code behind `enforce_principal`, and no handler checks a role, a participant claim, a study or the immutability of `owner`/`study_id`. The work is mechanical but wide: one auth floor, one policy engine driven by a Python table that mirrors ADR 0007, an `authorize(module, op)` dependency in each of 36 routers (253 routes), a handful of structural fixes (token claim, login eligibility, refresh, audit stamping, patch allowlists, Fitbit response filter), and client gates. No new third-party package is needed.

Three findings need a planner decision before tasks are written (see Open Questions): (1) ADR 0007's `self-member-conversation` predicate reads `Conversation.channels`, which the domain entity does not carry (the CB adapter drops it in `to_domain`), so it cannot be computed through today's ports; (2) two routes are outside the 36x7 table (`POST /v1/conversations:search` and `POST /v1/studies:lookup`) and need a policy mapping; (3) archived-record fail-closed rules cannot be observed on the legacy adapters (archive copies and leaves the original readable, ADR 0003). The refresh path (must-verify a) works for staff already, but lacks any eligibility re-check and pins `participant` from the session instead of the user record. `UserCreate`/`UserUpdate` accept `roles`; that is safe only because the `user` row is admin-only, but the 20-odd `*Update` schemas that accept `study_id` and the hand-rolled participant patch (accepts `user_id`) need the allowlist.

**Primary recommendation:** Build `openwellness_api/authz/` (policy table + `authorize()` dependency returning an `Access` object) first, attach a strict `get_principal` as the `v1.include_router(..., dependencies=[...])` floor, then roll the 36 routers in four shape groups; keep every denial 404 byte-identical to a genuine missing-record 404.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Bearer verification, 401 floor | API / Backend (`deps/principal.py`, `v1.py`) | — | Only the API holds the signing secret (HS256 until Phase 3) |
| Role/scope decision (policy table) | API / Backend (`authz/`) | Database / Storage (record reads via ports) | Table is API-owned; it reads Participant/record fields through existing ports, never SQL |
| Coach study claim minting | API / Backend (`auth/service.py`, `token_service.py`) | Database / Storage (`User.roles.coach.studies`) | ADR 0006: re-minted from the user record at login and refresh |
| Owner binding / study binding on writes | API / Backend (`common/handlers.py`, `authz/`) | Database / Storage | Server derives `study_id`; never from the body |
| Fitbit token redaction | API / Backend (response filter in `resources/fitbit.py`) | — | ADR 0007: both fields null for non-admins |
| Client role gates (UX only) | Browser / Client (dashboard), Mobile (KMP) | — | D-02: not a security boundary |
| Docs gating | API / Backend (`main.py`, `config.py`) | — | D-09 |
| Dev seed | API tooling script over repository ports | Database / Storage | D-04 |

## Standard Stack

### Core (all already in the lockfile; nothing new to install)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.136.3 (locked) [VERIFIED: ran `fastapi.__version__` in `backend/api` venv] | Router-level `dependencies=`, per-route `Depends` | Project stack; dependency introspection (`route.dependant.dependencies`) makes the structural test possible |
| PyJWT | 2.13.0 (locked) [CITED: CLAUDE.md stack section] | Access token claims (`coach_studies` added) | Existing `JwtTokenService` |
| Pydantic / pydantic-settings | 2.13.4 / >=2.3 [CITED: CLAUDE.md] | Docs-flag setting, claim shape validation | Existing |
| pytest + TestClient, fakeredis, mongomock | existing | CI flow without live infra | Existing suites (232 api tests pass in 23 s; 88 core) [VERIFIED: ran both suites this session] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Ktor / Koin / kotlin-test (mobile) | Ktor 3.5.0 [CITED: CLAUDE.md] | Mobile gate and a MockEngine test that the bearer is attached on a non-auth path | D-02, D-11 |
| Vitest + MSW (dashboard) | existing | Only if the dashboard gate needs a regression test; no behavior change planned | D-02 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Router-level dependency in `v1.py` | ASGI middleware that checks the Authorization header | Middleware would give 401 even for anonymous malformed JSON (probe below returned 422 for that one case); costs a second verification site. Recommend dependency only (AUTH-01 says "at the router"). |
| Python policy table | casbin / oso / fastapi-permissions | D-14 locks a Python table; none of those are in the stack. Not recommended. |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed or upgraded in this phase. The Package Legitimacy Gate does not apply.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Client (dashboard / mobile)                          anonymous
   |  Authorization: Bearer <access JWT>                |
   v                                                    v
FastAPI app (create_app)
   |-- /healthz  ------------------------------------------> 200 (no data)
   |-- /docs /redoc /openapi.json : mounted only if API_ENABLE_DOCS
   |-- /v1/auth:*  (no floor; own anti-enumeration rules) --> AuthService
   |                                                           |- OTP store (Redis)
   |                                                           |- user/participant repos
   |                                                           '- mint_access(roles, participant, coach_studies)
   '-- /v1/<36 resource routers>   include_router(dependencies=[Depends(get_principal)])
          |
          | 1. FLOOR: get_principal  -> verify_access(token) else 401 UNAUTHENTICATED
          |         (no X-Principal-Id, no anonymous fallback)
          v
       route handler  Depends(authorize("<module>", "<op>"))   (op in get|list|create|patch|delete|undelete|purge)
          | 2. DECIDE (authz/engine.py), per column the caller holds (admin / coach / participant-self):
          |       predicate satisfied?  --no--> contributes NOT_FOUND
          |       no predicate (cell none, scope "-") --> contributes FORBIDDEN
          |       satisfied and op in cell --> ALLOW ; satisfied and op not in cell --> FORBIDDEN
          |    any ALLOW -> proceed ; else any FORBIDDEN -> 403 PERMISSION_DENIED ; else 404 (same body as missing)
          v
       handler body:  _fetch -> access.check_record(entity)      (record-level scope: owner, study_id, membership)
                      lists  -> access.scope_list(items)          (D-08: scope first, then filter=, then paginate)
                      create -> study-binding (study_id from owner's Participant)
                      patch  -> apply_patch with immutable/privileged field denylist
                      audit  -> updated_by = principal.id (= sub), always
          v
       repository port (Couchbase/Mongo today; Postgres later) -> serialize_one -> (Fitbit: null tokens unless admin)
```

### Recommended Project Structure
```
backend/api/src/openwellness_api/
├── authz/
│   ├── __init__.py
│   ├── policy.py      # POLICY: dict[module, Row]; OPS; custom-method map; the D-14 table
│   ├── engine.py      # decide(); predicates; Access dataclass; authorize() dependency factory
│   └── scope.py       # participant lookup, coach_studies helpers, study-binding derivation
├── deps/principal.py  # strict get_principal; Principal gains coach_studies
├── auth/token_service.py  # AccessClaims + mint_access gain coach_studies
├── auth/service.py    # shared _login_eligible(), coach_studies derivation, refresh re-derive
├── common/handlers.py # apply_patch denylist, stamp_audit hard-assign, not_found reuse
├── config.py          # remove enforce_principal; add enable_docs to APISettings
├── main.py            # create_app(lifespan=..., settings=...) refactor; docs gating
└── v1.py              # floor dependency on resource routers only
backend/api/tests/
├── conftest.py        # token helper + "world" fixture + generic fakes for all 36 providers
├── test_policy_adr_match.py   # extend test_adr_policy_table.py row parsing (D-15)
├── test_route_enumeration.py  # AUTH-01/02
├── test_policy_matrix.py      # parametrized from POLICY (AUTH-03/04/05)
└── test_audit_and_mass_assignment.py
```

### Pattern 1: Strict principal and router floor
**What:** `get_principal` verifies the bearer or raises 401; `v1.py` attaches it to every resource router but not to `auth.build_router()`.
**When to use:** always; this is AUTH-01.
**Example:**
```python
# Source: probe run in this session against FastAPI 0.136.3 + current v1.py shape
def build_v1_router() -> APIRouter:
    v1 = APIRouter(prefix="/v1")
    for mod in RESOURCE_MODULES:
        v1.include_router(mod.build_router(), dependencies=[Depends(get_principal)])
    v1.include_router(auth.build_router())   # stays outside the floor
    return v1
```
Probe result (FastAPI 0.136.3): anonymous POST with no body -> 401; anonymous with a typed-but-invalid body -> 401; anonymous GET with bad query -> 401; anonymous POST with **malformed JSON** -> 422 (body parse precedes dependencies). Authenticated invalid body -> 422. The enumeration test therefore sends no body; the malformed-JSON-anonymous 422 is a known, harmless edge (no data returned). [VERIFIED: probe output this session]

### Pattern 2: `authorize(module, op)` as an introspectable callable
**What:** a callable object with `.module` and `.op` attributes used as `Depends(authorize("weight", "create"))`. It depends on `get_principal` (FastAPI caches it per request, so the floor and the policy share one verification), returns an `Access`.
**Why:** the structural test walks `app.routes`, reads `route.dependant.dependencies[*].call`, and asserts every non-exempt route has exactly one `authorize` whose `(module, op)` exists in `POLICY` and agrees with the HTTP method and path suffix (`POST ""` create, `GET ""` list, `GET /{id}` get, `PATCH` patch, `DELETE` delete, `POST ...:undelete`, `POST ...:purge`). A router that forgets it fails CI, which is the "anything missing is denied" half of D-14. [VERIFIED: introspection of `rt.dependant.dependencies[*].call.__name__` worked in probe]
```python
class authorize:                      # callable class, so tests can read .module/.op
    def __init__(self, module: str, op: str) -> None:
        self.module, self.op = module, op
    def __call__(self, request: Request, principal: Principal = Depends(get_principal)) -> Access:
        # path_params come from request.path_params (user / study); no DB read here except
        # the Participant lookups a predicate needs (coach write check, self-study).
        return engine.begin(request, principal, self.module, self.op)
```

### Pattern 3: D-06/D-07 decision function (one place)
For each column the caller holds, derive a verdict; take the best:
- **admin** (role `admin`): cell from table, no predicate. Admin cell always has all seven where listed.
- **coach** (role `coach`): predicate `coach-study`; cell `none` with scope `—` on that column means "no predicate" (rows `admin`, `app`, `device`, `fitbit`, `user`).
- **participant-self** (non-empty `participant` claim; for `user` row, `sub`): predicate from the row's Scope column.
- Satisfied + op in cell = ALLOW. Satisfied + op not in cell = FORBIDDEN. Not satisfied = NOT_FOUND. No predicate on the column = FORBIDDEN. Overall: any ALLOW wins; else any FORBIDDEN gives 403; else 404.
- Check worked examples: participant POST `/users/{other}/conditions` -> participant col NOT_FOUND, no coach col -> **404**; own id -> FORBIDDEN -> **403**; coach (not a participant) GET `/v1/devices/{id}` -> coach col has no predicate -> **403**; coach POST `/users/{p-in-study}/weights` -> predicate satisfied, `create` not in coach cell -> **403**, `{p-other-study}` -> **404**; coach+participant multi-role on own data (not in own coach studies) -> participant col FORBIDDEN, coach col NOT_FOUND -> **403** (union keeps "403 only in own scope").
- Segment-less create (e.g. POST `/v1/devices`, `/v1/fitbits`, `/v1/users`, `/v1/studies`, `/v1/conversations` by a participant): predicate is vacuously satisfied (no record to hide), so the answer is 403. State this in the ADR amendment. [ASSUMED] — D-06 does not spell it out.

### Pattern 4: Record-level scope is one helper per handler, not a rewrite
Every router's `_fetch` already calls `check_parent`. Extend the seam: `access.check_record(entity)` (404 via the same `not_found(...)` text) and `access.scope_list(items)`. Handlers swap `principal: Principal = Depends(get_principal)` for `access: Access = Depends(authorize(...))`, and use `access.principal` in `stamp_audit`/`apply_patch`. Roughly 3 touched lines per handler.

### Pattern 5: Lists (D-08), spelled out
- participant-self on `users/{user}/X`: path binding (`{user}` == `participant` claim) is the scope; the existing owner query already filters. One query, as today.
- coach on owner-scoped lists: query the **unfiltered** owner list for `{user}`; `scoped = [e for e in items if e.study_id in coach_studies]`; if `items` and not `scoped` -> 404; else continue with `scoped`; then apply `filter=` and paginate. For `goal` (`kind`, absent on `LegacyGoal`) and `message` (`subtype`, `condition`) do not reimplement the filter in Python: run the existing repo method with the filter and intersect by `id` with `scoped` (keeps repo semantics). [VERIFIED: `LegacyGoal` has no `kind`; goal.py:158-175 dispatches kind to a repo method]
- Top-level lists (`device`, `study`, `conversation`, `studyMessages`): filter in Python by the predicate and return 200 (possibly empty). D-08's 404-if-all-removed applies to the coach owner-scoped case only; say so in the amendment. [ASSUMED: D-08 scope reading]
- `participant` list (`studies/{study}/participants`): coach needs `{study}` in `coach_studies` else 404; the repo call `get_by_study_id(study)` already scopes.
- Pagination: lists fetch-then-paginate in memory (`paginate(items, params)`), so scoping before `paginate` keeps tokens correct. [VERIFIED: weight.py:146-147]

### Pattern 6: Write rules
- **study-binding (create, all callers):** `study_id` = `Participant.study_id` where `Participant.id == owner` (the `{user}` segment); non-empty supplied `study_id` differing -> 404; no Participant or empty `study_id` -> 404, even for admin. For `study_settings` the owner is `{study}` itself. For `conversation` (owner meaningless) require non-empty body `study_id`, and for coach it must be in `coach_studies`. Every `owner holds` value in ADR 0005's table is a participant id or a study id, so the "user id owner" branch of ADR 0007 has no rows today and need not be built. [VERIFIED: docs/adr/0005-owner-semantics.md classification table, lines 56-83]
- **coach write check:** on create/patch/delete/undelete of owner-scoped rows, also resolve `record.owner` (or `{user}` on create) to its Participant and require `Participant.study_id in coach_studies`. Exempt `participant_group`/`conversation` (record `study_id` alone). Fail closed (404).
- **patch immutability:** in `apply_patch` and the hand-rolled `participant.py` patch, drop `owner`, `study_id`, `updated_by`, `created_at`, `updated_at`, `id` for every caller; drop `user_id` (participant row) and `roles` (user row) unless the caller is admin. Unknown/forbidden keys are silently ignored (matches `extra="ignore"` and keeps the wire stable). [ASSUMED: ignore vs 400; ignoring keeps old clients working]

### Anti-Patterns to Avoid
- **`if "coach" in roles`:** role-string gates with no study check (Pitfall 2). Always go through `authorize`.
- **Authenticated = authorized:** the floor gives 401 only.
- **A different 404 body for out-of-scope:** `not_found(...)` and `check_parent` currently produce the same text (`"{collection}/{id} not found for users/{user}"`). Any new denial must raise `EntityNotFoundException` with the identical format, or existence leaks. [VERIFIED: handlers.py:141-169 and `format_name` usage in weight.py]
- **Reading roles from the request body or path:** only the verified token.
- **Applying `filter=` before scope.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT verification | New decode path | Existing `JwtTokenService.verify_access` | Already enforces iss/aud/exp/typ and claim shapes; Phase 3 swaps the algorithm behind it |
| AIP-193 error bodies | Hand-built dicts | `build_error(code, status, message)` + `HTTPException(detail=...)`; `not_found(...)` | Registered handler unwraps `detail`; wire stays stable |
| 404 for denied | Custom exception/text | `EntityNotFoundException` via `not_found` | Byte-identical to missing |
| Route list for the 401 test | Hardcoded path list | `app.routes` walk (`APIRoute.methods`, `.path`, `.dependant`) | Stays correct as routers change |
| ADR table parsing | Second parser | Extend `ROW` + `str.split("|")` in `test_adr_policy_table.py` | D-15 says extend it |
| Docs disabling | Custom middleware | `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` | With all three `None`, `app.routes` is empty (probe) |
| Immutable-field protection | Per-schema fields removed | One denylist in `apply_patch` | 20-odd `*Update` schemas accept `study_id` |

**Key insight:** the policy is a small data table plus one decision function; the cost is entirely in the 36-router rollout and the tests, so make the per-handler change tiny and structurally verifiable.

## Must-Verify Results

### (a) Refresh path with a staff user and null participant
- `_issue_credential(user, participant_id, ...)` accepts `participant_id: str | None` and passes it to `mint_access` and `session_store.create` (service.py:490-532). OTP store and refresh-session store both already accept/persist `None` (stored as `""`/`None`; `RefreshSession.participant_id: str | None`). [VERIFIED: otp_store.py:122,137,209; refresh_session_repository.py:26; mongo_refresh_session_repository.py:69,144]
- `refresh_token()` re-reads the user, requires only `user.is_active`, then `participant = result.participant_id or self._participant_pid(user)` (service.py:569) and re-mints roles from the user. A staff user therefore refreshes today. No test covers it.
- Gaps to close with D-01:
  1. No eligibility re-check at refresh. Add the shared `_login_eligible(user)` (active and (verified participant or coach/admin role)); a user who lost every usable role stops at the next refresh, consistent with ADR 0006's "re-minted at every refresh".
  2. The `participant` claim is pinned from the session (`result.participant_id`) rather than the current user record. Re-derive from the user (`_participant_pid(user)`); this also stops a removed participant role from living on for 30 days. Check the two existing refresh tests (`test_refresh_rotation_and_reuse_revokes_family`, `test_refresh_inactive_user_401`) still pass; they use participant users.
  3. Add `coach_studies` re-derivation here and in `_issue_credential` from one helper.
- Login code today (verbatim): `if not user.verified_id:` (service.py:294), `if not self._participant_pid(user):` (service.py:296), and in verify `or not self._participant_pid(user)` (service.py:330) are the three lines D-01 replaces with the shared predicate. The OTP-stored `participant_id` is already ignored in verify and re-derived. [VERIFIED: Read service.py]

### (b) `POST /v1/users` admin-only; `UserCreate` accepts `roles`; mass assignment
- `UserCreate` and `UserUpdate` both carry `roles: dict` (`schemas/user.py`), `is_active`, `email`. The `user` row grants participant-self `get` only and coach `none`, so create/patch/list/delete are admin-only; accepting `roles` is then correct (an admin assigns `roles.coach.studies`). Add shape validation for `roles.coach.studies` (list of strings) on admin write or treat malformed values as empty at mint time; the second is mandatory either way.
- ADR 0007 mass-assignment rule applies to **non-admin** writes: coach patch on `participant` (`ParticipantUpdate` includes `user_id`, `assigned_coach_id`, `is_active`; study_id is not in the schema, good) and participant-self/coach patches on 20-odd owner-scoped rows whose `*Update` carries `study_id` (e.g. `WeightUpdate.study_id`). The participant router patches with its own `setattr` loop, not `apply_patch` (participant.py:104-113), so the denylist must be applied in both places. [VERIFIED: Read schemas/participant.py, schemas/weight.py, resources/participant.py]
- `POST /v1/users` duplicate-email 409 oracle: closes automatically once the `user` create cell is admin-only; add a test that a coach and a participant get 403 on `POST /v1/users` before the body is evaluated for duplicates (authorize runs before body handling of dependencies, FastAPI evaluates dependencies before the handler).

### STATE.md blockers
- **Duplicate-email oracle:** closed by the `user` row (above) + test.
- **Fitbit tokens:** `Fitbit` response schema has `access_token` and `refresh_token` (schemas/fitbit.py). Null both for any non-admin caller after `serialize_one`; the participant-self `get` on own row is the only non-admin path. `FitbitCreate`/`FitbitUpdate` accept the tokens but are admin-only. [VERIFIED: Read schemas/fitbit.py]

## Common Pitfalls

### Pitfall 1: Tests that leak `X-Principal-Id` assumptions
**What goes wrong:** ~60 existing assertions use the anonymous `client` (`test_users_crud`, `test_weights_owner_crud`, `test_goals_carveout`, `test_error_mapping`, `test_pagination`, `test_participant_ids`, `test_repository_errors`, `test_auth_api`, `test_principal`, parts of `test_otp_store`) and `updated_by == "test-principal"`.
**How to avoid:** add conftest helpers first (`token_for(user, ...)`, `auth_client`/headers fixtures minting through `app.state.auth_container.token_service().mint_access`), then migrate suites in one task. `test_principal.py` and the `enforce_principal` probe in `test_auth_api.py` (lines ~517-575) are rewritten, not patched. Seeds: owner-scoped creates now require an existing Participant with a `study_id` (study-binding), so weights tests under `user-1` need a Participant fixture.
**Warning signs:** a test passing with no `Authorization` header.

### Pitfall 2: The test app is not the real app
**What goes wrong:** conftest builds `FastAPI(title="OpenWellness API (test)")` (conftest.py:292) with default docs routes and no `/healthz`; an enumeration test over that app proves nothing about D-09 or the real wiring.
**How to avoid:** refactor `create_app(*, lifespan=lifespan, settings=None)`; conftest calls `create_app(lifespan=None, settings=APISettings(enable_docs=False))`. [VERIFIED: main.py:97,109 and conftest.py:292]

### Pitfall 3: Only 8 of 36 providers are faked
**What goes wrong:** a policy-matrix test parametrized across all 36 rows hits real Couchbase/Mongo providers.
**How to avoid:** a generic in-memory fake registry in conftest covering every `RepositoryContainer` provider, supporting exactly the methods routers call: `get_by_id, create, save, delete, archive, unarchive, list_all, get_for_owner_between` plus `get_by_study_id` (participant), `get_by_name` (study), `get_all_for_owner_between`/`..._by_kind_between` (goal), `get_for_filters` (conversation). [VERIFIED: grep of `repo.<method>(` across resources/*.py, counts 36/36/36/36/36/36/26/8/1/1/1/1/1]

### Pitfall 4: Conversation membership predicate is not computable
**What goes wrong:** ADR 0007 `self-member-conversation` needs `Conversation.channels`. The domain `Conversation` has no `channels` field; `CBBaseEntity.to_domain` keeps only `entity_cls.valid_fields()`, so `channels` is dropped; the API never sets it on create. [VERIFIED: cb_base_entity.py to_domain filter; domain/models/conversation.py fields `kind`, `title`; grep of `channels` in core/src]
**How to avoid:** decision needed (Open Question 1). Participant-self cells for `conversation` must not default to open.

### Pitfall 5: `participant_group` fetch uses owner equality
**What goes wrong:** `participant_group.py` `_fetch` calls `check_parent(owner == {user})`, but ADR 0007 `self-member-group` says the `{user}` segment is the participant and the group's `participant_ids` must contain it, NOT owner equality; list must return groups whose `participant_ids` contains the claim, not `get_for_owner_between(user, ...)`. Needs its own fetch/list logic (ParticipantGroupRepository has no membership query; use `list_all()` + filter or a new port method). [VERIFIED: Read participant_group.py:44-52,125-145 and ParticipantGroup model `participant_ids: list[str]`]

### Pitfall 6: Custom methods outside the 36x7 table
`POST /v1/conversations:search` (conversation.py:106) accepts `channels` filters over **all** conversations and `POST /v1/studies:lookup` (study.py:94) returns any study by name. Deny-by-default would leave them with no table cell. Recommend: map `:search` to op `list` and `:lookup` to op `get`, both scope-filtered, and record the mapping in the ADR 0007 amendment. Add both to the enumeration test.

### Pitfall 7: Coach study ids from Mongo may not be plain strings
`MongoUser.roles: Any` (mongo_user.py:23). If `roles.coach.studies` holds ObjectIds, putting them in a JWT fails to encode. The API cannot import `bson` (an AST test forbids it, `test_source_invariants.py`). Derive with `[str(s) for s in studies if s]` after `isinstance(studies, list)`, else `[]`. Same defensive pattern as `_roles_list`.

### Pitfall 8: Archive state is invisible on legacy adapters
ADR 0007 says an archived Participant/group fails closed, but legacy `archive()` copies the doc and leaves the original readable (ADR 0003); no `deleted_at` exists on any domain entity today. Implement the check as `getattr(entity, "deleted_at", None)` in one helper so Phase 4/5 flip it on; do not invent an archived lookup now. [VERIFIED: grep found no `deleted_at` in core/src domain; ADR 0003 text]

### Pitfall 9: Token staleness and logout
Access tokens stay valid until expiry after logout or `is_active=False` (no per-request user read). ADR 0006 accepts 930 s for coach study changes; deactivation is not stated. Recommend accepting the same window and saying so in the ADR amendment (Open Question 4).

### Pitfall 10: Mobile gate placed after token persistence
`OpenWellnessAuthRepository.persistVerified` saves tokens, then returns the session; the VM then navigates. A gate in the VM would leave a staff token on disk. Gate inside `persistVerified` **before** `tokenStorage.saveTokens`, and best-effort revoke the just-issued refresh token (the dashboard only clears local state; the server session lingers up to 30 days). A new `AuthError` variant forces updates in `AuthErrorToUiText.kt` (exhaustive `when`) and `strings.xml`. [VERIFIED: Read OpenWellnessAuthRepository.kt, AuthErrorToUiText.kt, strings.xml line 23 pattern]

### Pitfall 11: Missing `Participant` for owner on create breaks fixtures and the UAT
study-binding fails closed for every caller, including admin, when the owner has no Participant or an empty `study_id`. The D-04 seed must create Study, Participant (with `study_id` and `user_id`) and the participant User (`roles.participant.pid`, `verified_id`), and the coach's `roles.coach.studies`.

### Pitfall 12: `.env.example` enabling docs gets copied to VMs
Called out in CONTEXT specifics. Config default must be off in code; `.env.example` sets it on with a comment; Phase 10/12 must set it off explicitly. Note it in the plan's follow-up list.

## Code Examples

### Token claim and Principal
```python
# token_service.py: add to AccessClaims and mint_access; tolerate tokens minted before this change
coach_studies: tuple[str, ...] = ()
...
claims["coach_studies"] = list(coach_studies)
...
raw = payload.get("coach_studies", ())
if not isinstance(raw, (list, tuple)) or not all(isinstance(s, str) for s in raw):
    raise InvalidAccessToken("malformed coach_studies claim")
```
Existing claim set verbatim from the code (token_service.py:62-71): `"typ": "access"`, `"participant": participant`, `"roles": list(roles)`. ADR 0004 names the study claim via ADR 0006 as `coach_studies`. [VERIFIED: token_service.py read; ADR 0006 line "The access token carries the list as the `coach_studies` claim (a list of strings)"]

### Strict principal (replaces fallback and `require_principal`)
```python
def get_principal(request: Request) -> Principal:
    header = request.headers.get("authorization") or ""
    if header[:7].lower() != "bearer " or not header[7:].strip():
        raise HTTPException(401, detail=build_error(401, "UNAUTHENTICATED", "Authentication required."))
    try:
        claims = request.app.state.auth_container.token_service().verify_access(header[7:].strip())
    except InvalidAccessToken:   # import lazily if the cycle note in principal.py still applies
        raise HTTPException(401, detail=build_error(401, "UNAUTHENTICATED", "Authentication required."))
    return Principal(id=claims.sub, roles=claims.roles, participant=claims.participant,
                     coach_studies=claims.coach_studies, is_authenticated=True)
```
Do not add a `WWW-Authenticate` header: the mobile client is built around preemptive bearer (`sendWithoutRequest { true }`, HttpClientFactory.kt comment: "The backend's 401s carry no WWW-Authenticate challenge"), so changing 401 headers is a wire change. [VERIFIED: HttpClientFactory.kt read]

### Docs gating
```python
class APISettings(OpenWellnessSettings):
    enable_docs: bool = False          # env API_ENABLE_DOCS
...
kw = {} if settings.enable_docs else dict(docs_url=None, redoc_url=None, openapi_url=None)
app = FastAPI(title=settings.title, lifespan=lifespan, **kw)
```
Probe: `FastAPI(docs_url=None, redoc_url=None)` still serves `/openapi.json`; only all three `None` yields zero routes. [VERIFIED: probe this session]

### Login eligibility shared predicate (D-01/D-03/D-05)
```python
def _is_staff(user) -> bool:
    roles = user.roles if isinstance(user.roles, dict) else {}
    return "coach" in roles or "admin" in roles

def _login_eligible(self, user) -> bool:
    if user is None or not user.is_active:
        return False
    if self._is_staff(user):
        return True                                   # D-03: verified_id waived
    return bool(user.verified_id) and bool(self._participant_pid(user))
```
Use in `_eligible_login_user`, `verify_login_code`, and `refresh_token`. Role keys come from the dict keys exactly as `_roles_list` does today (`list(roles.keys())`). [VERIFIED: service.py:142-149]

### Fitbit response filter
```python
row = serialize_one(entity, Fitbit, collection=_COLLECTION)
if not access.principal.is_admin:
    row["accessToken"] = None; row["refreshToken"] = None   # wire keys are camelCase via by_alias
```
Apply to `get`, `list`, `create`, `patch` and `undelete` responses (any path that serializes a Fitbit).

### Route enumeration test skeleton
```python
EXEMPT_PREFIXES = ("/v1/auth:",); EXEMPT = {"/healthz"}
for r in app.routes:
    if not isinstance(r, APIRoute): continue
    if r.path in EXEMPT or r.path.startswith(EXEMPT_PREFIXES): continue
    for m in r.methods:
        url = re.sub(r"\{[^}]+\}", "x", r.path)
        assert client.request(m, url).status_code == 401, (m, r.path)
```
With docs disabled, `app.routes` contains no docs entries, so nothing else is exempt (D-09). Also assert `"enforce_principal" not in AuthSettings.model_fields` and no `X-Principal-Id` text under `backend/api/src` (AST/text invariant in `test_source_invariants.py` style).

### ADR cell parse (D-15)
```python
cells = [c.strip() for c in line.strip().strip("|").split("|")]
module, route, scope, anon, psel, coach, admin = cells
ops = lambda s: frozenset() if s == "none" else frozenset(x.strip() for x in s.split(","))
```
Existing `ROW` regex `^\|\s*`[a-z_]+`\s*\|` matches the 36 policy rows only (predicate and data-class rows contain hyphens). [VERIFIED: test_adr_policy_table.py:14 and ADR 0007 rows]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Permissive `require_principal` logging would-be 401s | Strict floor, no flag | This phase (D-10) | Delete `enforce_principal`, `require_principal`, the `X-Principal-Id` read, README paragraph |
| Anonymous routes + `check_parent` as "auth" | Table-driven scope + role | This phase | `check_parent` stays as a storage-consistency check, no longer the control |
| HS256 shared secret | EdDSA/JWKS | Phase 3 (not here) | Keep `verify_access` as the single seam so Phase 3 swaps one implementation |

**Deprecated/outdated:** `AuthSettings.enforce_principal` (config.py:84 `enforce_principal: bool = False`), `require_principal`, and the `x_principal_id` fallback (principal.py:95). A stale `API_AUTH_ENFORCE_PRINCIPAL` in a deployment `.env` is harmlessly ignored (`extra="ignore"`, settings.py:46).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Segment-less create by a participant/coach is "in scope" and so answers 403, not 404 | Pattern 3 | Behavior test expectations flip for ~5 rows; fix is a one-line rule in the engine plus the ADR amendment |
| A2 | Top-level lists (device, study, conversation, studyMessages) filter silently and return 200 (D-08's 404 rule applies only to coach owner-scoped lists) | Pattern 5 | Different empty-vs-404 semantics for a few lists |
| A3 | Forbidden patch keys are silently ignored, not 400 | Pattern 6 | An older client sending `studyId` would start getting 400s if the team prefers strict |
| A4 | `:search` maps to op `list` and `:lookup` to op `get`, scope-filtered | Pitfall 6 | Needs an ADR 0007 amendment; if the developer prefers admin-only these become 403 for others |
| A5 | Accept the 930 s staleness window for deactivated users and logout (no per-request user read) | Pitfall 9 | If not acceptable, add a user read per request (extra datastore round trip on every call) |
| A6 | Mailpit or any local SMTP sink is acceptable for UAT until Phase 9 ships a mail catcher | Environment Availability | UAT cannot receive OTPs; SMTP is the only OTP channel and the code is never logged |
| A7 | UAT on legacy stores requires developer-supplied Couchbase and Mongo; Postgres adapters do not exist until Phases 4-5 | Environment Availability | UAT is blocked without them |

## Open Questions

1. **Conversation membership predicate (`self-member-conversation`) is not computable.**
   - What we know: ADR 0007 requires `Conversation.channels` to contain `participantGroup:{g.id}`; the domain `Conversation` has no `channels`, the CB persistence class holds it but `to_domain` drops it, and the API never writes it. Mobile has no conversation code yet.
   - What's unclear: whether Phase 2 should add `channels` to the domain entity (touches the CB/Mongo mappers and the `Conversation` wire shape is unchanged if not exposed) or fail closed.
   - Recommendation: for Phase 2, keep the table cells as in ADR 0007 (D-15 match), but make the predicate return no match (participant-self conversation get/list -> 404 / empty list) with a clearly named TODO, and record in the ADR amendment that Phase 6 defines the stored membership link. This is closed by default and no participant data leaks. If the developer wants it live now, add `channels: list[str] = field(default_factory=list)` to the domain entity and map it in `CBConversation`; plan that as an explicit extra task. STATE.md already lists this predicate as a Phase 6 blocker.

2. **Policy cells for `conversations:search` and `studies:lookup`.** See Pitfall 6 and A4. Needs a one-line developer confirmation (amendment text).

3. **Archived/deleted checks (ADR 0007 fail-closed on archived Participant or group).** Not observable on legacy adapters. Recommendation: single `_is_archived()` helper using `getattr(..., "deleted_at", None)`; real behavior arrives with Phase 5.

4. **Per-request `is_active` re-check.** Recommend not adding it (A5); state the accepted window in the amendment.

5. **Mobile "authorized resource call per role" (D-11).** The mobile app has no resource-call code and no screen that makes one (Home is a placeholder). Recommendation: the mobile proof is (a) an `androidHostTest` with Ktor `MockEngine` asserting the preemptive `Authorization` header on a non-`auth:` path, (b) the already-authenticated `auth:revokeToken all=true` path in the live UAT, and (c) the server-side pytest flow with real tokens. Say so in the UAT doc rather than adding a screen.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | all backend commands | yes | 0.12.15 | — |
| Python (via uv, 3.12+) | backend | yes (venv resolves to a newer interpreter) | `.venv` python3.14 [VERIFIED: path in pytest warning] | system `python3` is 3.9.6, do not use it |
| Docker | UAT stack (Redis, mail sink) | CLI present (29.8.2); daemon not confirmed | 29.8.2 | run Redis/Mailpit elsewhere |
| Node | dashboard tests | yes but v26.13.0 | 26.13.0 | CI pins Node 22 because Node 25+ built-in localStorage breaks jsdom suites (STATE.md); use `nvm`/Node 22 for dashboard tests |
| Java/JDK | Kotlin host tests, Android build | **no JRE found** | — | Install a JDK (Gradle daemon JVM is configured in `gradle-daemon-jvm.properties`); Kotlin tests otherwise run only in CI |
| Xcode | iOS simulator UAT | `xcodebuild` present (error output on bare call) | not confirmed | — |
| Redis (local) | live API, OTP | not installed locally | — | `docker run redis:7-alpine` (as compose) |
| Couchbase + Sync Gateway, Mongo | live API for D-12 manual UAT | not installed locally | — | developer-provided instances via `.env` (Postgres adapters arrive in Phases 4-5) |
| SMTP sink | OTP delivery for UAT | not installed | — | any local SMTP catcher [ASSUMED: Mailpit]; Phase 9 adds the official one |

**Missing dependencies with no fallback:** live Couchbase/Mongo for the manual UAT (developer must provide), a JDK for local Kotlin test runs.
**Missing dependencies with fallback:** Redis (docker), SMTP sink (docker).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8 + FastAPI TestClient (api); Vitest 4.1 (dashboard); kotlin-test + MockEngine (mobile) |
| Config file | no pytest.ini; `backend/api/pyproject.toml` dev extra; conftest at `backend/api/tests/conftest.py` |
| Quick run command | `cd backend/api && uv run --frozen pytest -q -x tests/test_route_enumeration.py tests/test_policy_matrix.py tests/test_adr_policy_table.py` |
| Full suite command | `cd backend && uv sync --frozen --extra dev && (cd core && uv run --frozen pytest -q) && (cd api && uv run --frozen pytest -q) && (cd scheduler && uv run --frozen pytest -q) && uv run --frozen pyright` |

Baseline this session: api 232 passed (23.5 s), core 88 passed (0.4 s). pyright scope is `core/src` and `core/tests` only (`pyrightconfig.json` include), so api type errors are not caught by it; keep api code annotation-clean by hand. [VERIFIED: pyrightconfig.json read]

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Floor 401 on every non-exempt route; flag/header gone | integration + source invariant | `pytest tests/test_route_enumeration.py tests/test_source_invariants.py -q` | Wave 0 (new) / extend existing |
| AUTH-02 | Enumerates `app.routes`; each has `authorize(module, op)` matching method/path | integration (structural) | `pytest tests/test_route_enumeration.py -q` | Wave 0 |
| AUTH-02 / D-15 | Python POLICY equals ADR 0007 cells; 36 rows; op cells valid | unit | `pytest tests/test_adr_policy_table.py -q` | extend existing |
| AUTH-03 | Own `{user}` ok; other's 404; hostile `filter=` (`owner=...`) 400 and `filter=kind=1` on other's path 404 | parametrized integration | `pytest tests/test_policy_matrix.py -k owner -q` | Wave 0 |
| AUTH-04 | Non-admin 403 on admin/app/user list and write | parametrized | `pytest tests/test_policy_matrix.py -k admin -q` | Wave 0 |
| AUTH-05 | Coach in-study ok, other-study 404, empty `coach_studies` matches nothing, write also checks owner Participant study, cross-study create refused, study-binding, D-08 404-vs-empty-200 | parametrized | `pytest tests/test_policy_matrix.py -k coach -q` | Wave 0 |
| AUTH-06 | Forged `X-Principal-Id` ignored; `updated_by == sub` on create+patch incl. conversation; participant-claim vs sub distinction | integration | `pytest tests/test_audit_and_mass_assignment.py -q` | Wave 0 |
| D-01/D-03/D-05 | Staff login, refresh, no-role lockout, uniform responses, coach with empty list | unit (service) + API | `pytest tests/test_auth_service.py tests/test_auth_api.py -q` | extend existing |
| D-06/D-07 | 404-before-403 ordering, multi-role union | parametrized | `pytest tests/test_policy_matrix.py -k "order or multirole" -q` | Wave 0 |
| D-09 | Docs routes absent by default, present when `API_ENABLE_DOCS=1` | unit | `pytest tests/test_docs_gating.py -q` | Wave 0 |
| ADR mass-assignment | patch cannot change owner/study_id/updated_by/user_id/roles for non-admin; Fitbit tokens null for non-admin | integration | `pytest tests/test_audit_and_mass_assignment.py -q` | Wave 0 |
| AUTH-09 | Sign-in -> authorized call -> refresh -> authorized call -> sign-out per role on fakes | integration flow | `pytest tests/test_e2e_roles_flow.py -q` | Wave 0 |
| AUTH-09 (mobile) | Gate rejects null-participant session before token save; bearer attached on non-auth path | Kotlin host test | `cd frontend/mobile && ./gradlew testAndroidHostTest` | Wave 0 (needs JDK) |
| AUTH-09 (dashboard) | Existing role gate unchanged | Vitest | `cd frontend/dashboard && npm test` | exists (loginFlow.test.tsx) |
| AUTH-09 (manual) | Live UAT with D-04 seed on dashboard, Android, iOS simulator | manual only (needs live stores, SMTP, devices) | UAT checklist in phase dir | Wave 0 (doc) |

### Sampling Rate
- **Per task commit:** the quick command for the touched area (< 30 s).
- **Per wave merge:** full backend suite command above.
- **Phase gate:** full suite green, dashboard `npm test`, Kotlin `testAndroidHostTest` (CI), manual UAT signed, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/conftest.py`: `create_app`-based app fixture, token helper, "world" fixture (studies A and B, participants pA/pB with users, coach A, coach with empty list, coach A+B, admin, dual-role coach+participant), generic fakes for all 36 providers.
- [ ] `tests/test_route_enumeration.py`, `tests/test_policy_matrix.py`, `tests/test_audit_and_mass_assignment.py`, `tests/test_docs_gating.py`, `tests/test_e2e_roles_flow.py`.
- [ ] Migrate `test_users_crud`, `test_weights_owner_crud`, `test_goals_carveout`, `test_error_mapping`, `test_pagination`, `test_participant_ids`, `test_repository_errors`, `test_principal`, `test_auth_api` off the anonymous client; delete the `enforce_principal` probe tests.
- [ ] Mobile: gate test + MockEngine bearer test (requires JDK locally; CI has it).
- [ ] Framework install: none.

## Security Domain

`security_enforcement` is enabled (absent = enabled); ASVS level 1, block on high (`.planning/config.json`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Email-OTP unchanged; staff eligibility per D-01/D-03; uniform responses preserved |
| V3 Session Management | yes | Refresh rotation unchanged; re-mint claims from user at refresh; eligibility re-check at refresh |
| V4 Access Control | yes (primary) | Deny-by-default floor + policy table + scope-before-role + study-binding |
| V5 Input Validation | yes | Claim shape validation (`coach_studies` list of str), patch denylist, existing Pydantic |
| V6 Cryptography | no change | JWT signing stays HS256 until Phase 3; do not hand-roll |
| V7 Logging | yes | No tokens, emails or OTPs in logs; log denials as `principal id`, module, op only |
| V8 Data Protection | yes | Fitbit OAuth tokens never leave the server for non-admins |
| V13 API | yes | AIP-193 envelopes unchanged; docs off by default |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR across `{user}` | Information disclosure | `{user}` must equal `participant` claim; record `owner` check; 404 identical to missing |
| Coach over-reach across studies | Elevation of privilege | `coach_studies` claim plus owner Participant study on writes |
| Cross-study create via body `study_id` | Tampering | Server derives `study_id`; differing value refused |
| Mass assignment (`owner`, `study_id`, `roles`, `user_id`, audit) | Tampering / EoP | Denylist in `apply_patch` and participant patch |
| Forged `X-Principal-Id` | Spoofing / Repudiation | Header never read; `updated_by` = `sub` |
| `filter=` widening scope | Information disclosure | Scope before filter; grammar cannot name `owner`/`study_id`; hostile-filter test |
| Existence oracle via distinct 404/403/409 text | Information disclosure | Same exception text; `POST /v1/users` admin-only closes the 409 |
| Fitbit token disclosure | Information disclosure | Response filter for non-admin |
| Anonymous docs/openapi enumeration | Information disclosure | Off by default |
| Stale roles in 15-min token | Elevation of privilege | Re-mint at refresh; accept 930 s (ADR 0006) |
| Staff token on a participant-only mobile app | EoP (UX layer) | Mobile gate before persist plus server-side enforcement remains the boundary |

## Sources

### Primary (HIGH confidence)
- Repository files read this session: `docs/adr/0003..0007`, `backend/api/src/openwellness_api/{main,v1,config}.py`, `deps/{principal,container,auth_container}.py`, `auth/{service,token_service,router,session_store,errors}.py`, `common/{handlers,filter}.py`, `schemas/{user,participant,weight,fitbit,conversation,_base}.py`, `resources/{weight,goal,user,participant,conversation,study,study_message,study_settings,device,participant_group,message}.py`, `backend/api/tests/{conftest,test_adr_policy_table,test_source_invariants,test_principal,...}.py`, `backend/core/.../domain/models/*`, `adapters/couchbase/model/cb_base_entity.py`, `cb_participant_group.py`, `frontend/dashboard/src/core/auth/{jwt,RequireAuth}.ts*`, `features/auth/hooks/useLogin.ts`, `frontend/mobile/.../OpenWellnessAuthRepository.kt`, `HttpClientFactory.kt`, `AuthErrorToUiText.kt`.
- Runtime probes this session: FastAPI 0.136.3 dependency ordering; `docs_url/redoc_url/openapi_url=None` route sets; full-app route enumeration (265 routes); baseline test runs.

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` Pitfalls 2 and 3 (project research).

### Tertiary (LOW confidence)
- Mailpit as the SMTP sink for UAT (A6), not verified.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new packages.
- Architecture: HIGH for floor, engine and rollout; MEDIUM for the few ADR gaps (conversation membership, custom methods, archived checks), flagged as Open Questions.
- Pitfalls: HIGH, each tied to a read file or a probe.

**Research date:** 2026-11-04
**Valid until:** 2026-12-04 (stable; invalidated if Phase 3 lands first or ADR 0007 is amended)
