# Phase 2: Route Authentication & Authorization - Pattern Map

**Mapped:** 2026-11-04
**Files analyzed:** 22 (new/modified groups)
**Analogs found:** 19 / 22
All analog paths below are git-tracked (checked `deps/principal.py`; all others are under tracked `backend/api/src`, `backend/api/tests`, `frontend/`).

Base paths: `API=backend/api/src/openwellness_api`, `T=backend/api/tests`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `API/authz/policy.py` (new) | config (policy table) | transform | ADR 0007 table + `T/test_adr_policy_table.py` ROW parse | partial |
| `API/authz/engine.py` (new, `authorize`, `Access`) | middleware/dependency | request-response | `API/deps/principal.py` (`require_principal`) | role-match |
| `API/authz/scope.py` (new) | service/utility | CRUD (port reads) | `API/common/handlers.py` `check_parent` | role-match |
| `API/deps/principal.py` (modify: strict, `coach_studies`) | middleware | request-response | itself (lines 58-136) | exact |
| `API/v1.py` (modify: floor route class) | route aggregator | request-response | itself | exact |
| `API/main.py` (modify: `create_app(lifespan, settings)`, docs gating) | config/factory | request-response | itself (lines 95-116) | exact |
| `API/config.py` (modify: drop `enforce_principal`, add `enable_docs`) | config | - | `APISettings` in same file | exact |
| `API/auth/token_service.py` (modify: `coach_studies` claim) | service | transform | itself (`mint_access`/`verify_access`) | exact |
| `API/auth/service.py` (modify: `_login_eligible`, refresh) | service | request-response | itself (`_eligible_login_user`, `verify_login_code`, `_roles_list`) | exact |
| `API/common/handlers.py` (modify: `apply_patch` denylist, `stamp_audit` hard-assign) | utility | CRUD | itself (lines 100-138) | exact |
| `API/resources/*.py` x36 (add `authorize`, `check_record`, `scope_list`) | controller | CRUD | `API/resources/weight.py` | exact |
| `API/resources/participant_group.py`, `participant.py`, `goal.py`, `fitbit.py`, `conversation.py`, `study.py` (special cases) | controller | CRUD | `weight.py` + own file | role-match |
| `T/conftest.py` (modify: `create_app`, token helper, world fixture, 36 fakes) | test | - | itself (~line 280-330) | exact |
| `T/test_route_enumeration.py` (new) | test | request-response | `T/test_source_invariants.py` (structural walk) + RESEARCH skeleton | partial |
| `T/test_policy_matrix.py`, `test_audit_and_mass_assignment.py`, `test_docs_gating.py`, `test_e2e_roles_flow.py` (new) | test | request-response | `T/test_weights_owner_crud.py` (client style) | role-match |
| `T/test_adr_policy_table.py` (extend, D-15) | test | transform | itself | exact |
| dev seed script (new) | utility/script | batch | `backend/core/scripts/check_no_fstring_n1ql.py` (script layout only) | partial |
| `frontend/mobile/.../OpenWellnessAuthRepository.kt` (gate before persist) | service | request-response | itself `persistVerified` (94-107) | exact |
| mobile `AuthError` variant + `AuthErrorToUiText.kt` + `strings.xml` | model/ui | - | dashboard `NotAuthorized` | role-match |
| `frontend/dashboard/src/core/auth/jwt.ts` | utility | - | unchanged; model for mobile gate | exact |
| `backend/api/README.md`, `.env.example`, ADR 0007 amendment | docs | - | n/a | none |
| UAT doc (phase dir) | docs | - | none | none |

## Pattern Assignments

### `API/deps/principal.py` (strict floor)
**Analog:** itself. Replace lines 58-136. Keep `Principal` dataclass (36-55), add `coach_studies: tuple[str, ...] = ()`. Keep the circular-import note (lines 15-20): `build_error` from leaf `..errors.responses`; import `InvalidAccessToken` lazily or keep broad except mapped to 401.

Existing verify seam to keep (lines 74-86):
```python
auth_header = request.headers.get("authorization") or ""
if auth_header[:7].lower() == "bearer ":
    token = auth_header[7:].strip()
    ...
    token_service = request.app.state.auth_container.token_service()
    claims = token_service.verify_access(token)
    return Principal(id=claims.sub, roles=tuple(claims.roles),
                     participant=claims.participant, is_authenticated=True)
```
401 envelope to reuse (lines 123-126):
```python
raise HTTPException(status_code=401,
    detail=build_error(401, "UNAUTHENTICATED", "Authentication required."))
```
Delete: `x_principal_id` Header param/fallback (95), `require_principal` (98-136), `enforce_principal` read. No `WWW-Authenticate` header (mobile preemptive bearer).

### `API/v1.py` (floor)
Current (9-16): loop `v1.include_router(mod.build_router())`; auth included separately. Set `FloorRoute` on each router's routes before including it, per plan 02-03: the developer chose 401 for every anonymous request, including an unparseable body, and a router-level dependency runs after FastAPI parses the body. Leave `v1.include_router(auth.build_router())` untouched.

### `API/main.py` (docs gating, testable factory)
Current `create_app()` (95-116) builds `APISettings()` and `FastAPI(title=..., lifespan=lifespan)`. Change to `create_app(*, lifespan=lifespan, settings=None)`; when `not settings.enable_docs` pass `docs_url=None, redoc_url=None, openapi_url=None` (all three needed). Keep CORS + `register_exception_handlers` + `/healthz`. Keep module-level `app = create_app()` (119).

### `API/auth/token_service.py` (claim)
Analog: itself. `mint_access(self, *, user_id, participant=None, roles=())` builds `claims` dict (31-41); add `coach_studies: Sequence[str] = ()` param and `"coach_studies": list(coach_studies)`. `AccessClaims` dataclass (above line 40) gains `coach_studies: tuple[str, ...] = ()`. In `verify_access` after the `typ` check (64-67) follow the shape-validation style and raise `InvalidAccessToken` on malformed; tolerate absent claim (default `()`).

### `API/auth/service.py` (D-01/D-03)
Replace three checks: `if not user.verified_id` / `if not self._participant_pid(user)` (~294-297, in `_eligible_login_user`) and the `or not user.verified_id or not self._participant_pid(user)` tuple (~328-333, `verify_login_code`). Also add to `refresh_token` (~569, currently `participant = result.participant_id or self._participant_pid(user)`). Role-keys pattern to copy for `_is_staff` (142-149):
```python
roles = getattr(user, "roles", None)
roles = roles if isinstance(roles, dict) else {}
return list(roles.keys())
```
Coach studies derivation: `isinstance(studies, list)` then `[str(s) for s in studies if s]` (Pitfall 7, no `bson` import; `T/test_source_invariants.py` forbids it). Uniform failures: `raise errors.invalid_code()` (auth/errors.py:39).

### `API/common/handlers.py`
`apply_patch` (100-119): add denylist `{owner, study_id, updated_by, created_at, updated_at, id}` skip inside the `for key, value in body.model_dump(exclude_unset=True).items()` loop; keep `entity.updated_by = principal.id` (118-119).
`stamp_audit` (122-138): change `payload.setdefault("updated_by", principal.id)` to `payload["updated_by"] = principal.id` (D-16/AUTH-06).
Denial 404 must reuse byte-identical text from `check_parent` (156-159) / `not_found` (163-169):
```python
raise EntityNotFoundException(f"{collection}/{getattr(entity,'id','?')} not found for {parent}/{parent_id}")
```
Extend `check_parent` seam with `access.check_record(entity)` rather than new exception text.

### 36 resource routers (controller, CRUD)
**Analog:** `API/resources/weight.py` (full file, 162 lines). Per-handler diff is ~3 lines:
- imports (13, 30): add `from ..authz.engine import Access, authorize`; drop `Principal, get_principal` where unused.
- Replace `principal: Principal = Depends(get_principal)` (lines 59, 91) with `access: Access = Depends(authorize("weight", "create"))`; add the dependency to the no-principal handlers too (get 75-78, delete 104-106, undelete 112-114, purge 122-124, list 130-136) since every route must carry exactly one `authorize` (structural test).
- `_fetch` (47-53): after `check_parent(...)` call `access.check_record(entity)`.
- create (62-66): `stamp_audit(..., principal=access.principal)`; add study-binding; for patch `apply_patch(entity, body, principal=access.principal)` (95).
- list (146-147): `items = repo.get_for_owner_between(user, rng.start, rng.end)` then `items = access.scope_list(items)` (D-08, before `filter=`, before `paginate(items, params)`).
Op names per method: POST "" create, GET "" list, GET /{id} get, PATCH patch, DELETE delete, `:undelete`, `:purge`. Router registration stays via `RESOURCE_MODULES` (`resources/__init__.py`).

Special cases (read these files before planning, per RESEARCH):
- `resources/participant.py` patch loop (lines ~100-113) uses its own `setattr` loop, not `apply_patch`; apply same denylist plus `user_id` for non-admin.
- `resources/participant_group.py` `_fetch` (44-52) and list (125-145) use owner equality; needs membership logic (Pitfall 5).
- `resources/fitbit.py`: null `accessToken`/`refreshToken` after `serialize_one` for non-admin on get/list/create/patch/undelete.
- `resources/conversation.py` (`:search`, line ~106), `resources/study.py` (`:lookup`, ~94): map to list/get ops (Open Question 2).
- `resources/goal.py`: filter via existing repo kind methods, intersect by id with scoped list (Pattern 5).

### `T/conftest.py`
Replace the hand-built app (292-297):
```python
instance = FastAPI(title="OpenWellness API (test)")
register_exception_handlers(instance)
instance.include_router(build_v1_router())
```
with `create_app(lifespan=None, settings=APISettings(enable_docs=False))`. Keep the auth-container override block (305-330: `AuthSettings()`, `JwtTokenService(settings=..., clock=default_clock)`, `RedisOtpStore(redis=fakeredis.FakeRedis(decode_responses=True), ...)`, `MongoRefreshSessionRepository(collection=mongomock...)`). Add `token_for(...)` helper using `auth_container.token_service().mint_access(user_id=..., participant=..., roles=..., coach_studies=...)`. Fakes registered via `container.repositories.<provider>.override(providers.Object(fake))` (`_IFACE_TO_PROVIDER`); extend to all 36 providers.

### `T/test_adr_policy_table.py` (D-15)
Extend (lines 14, 19-23). Current parse takes only cell 0. Add:
```python
cells = [c.strip() for c in line.strip().strip("|").split("|")]
module, route, scope, anon, psel, coach, admin = cells   # strip backticks from module
ops = lambda s: frozenset() if s == "none" else frozenset(x.strip() for x in s.split(","))
```
and assert equality against `authz.policy.POLICY`. Keep `assert len(rows) == 36`.

### `T/test_route_enumeration.py`
Structural-test style: `T/test_source_invariants.py` (ast walk, `BACKEND = Path(__file__).resolve().parents[2]`). Route walk: use RESEARCH "Route enumeration test skeleton" (`app.routes`, `APIRoute`, regex-substitute `{param}`, no body, expect 401, exempt `/v1/auth:` prefix and `/healthz`). Also assert each route's `route.dependant.dependencies[*].call` has an `authorize` instance whose `(module, op)` is in `POLICY`. Add a source invariant: no `X-Principal-Id` / `enforce_principal` text under `backend/api/src`.

### Mobile gate
**Analog:** `OpenWellnessAuthRepository.kt` `persistVerified` (94-107):
```kotlin
is Result.Success -> {
    val session = result.data.toAuthSession()
    tokenStorage.saveTokens(session.tokens.accessToken, session.tokens.refreshToken)
    invalidateBearerCache()
    Result.Success(session)
}
```
Insert the null-`participant` check before `saveTokens` returning a new `AuthError` variant (best-effort revoke refresh). Update `AuthErrorToUiText.kt` exhaustive `when` and `strings.xml` (pattern near line 23). Dashboard model: `features/auth/model/errors.ts:19` (`{ kind: 'NotAuthorized' }`), `useLogin.ts:320` (`authErrorMessage({ kind: 'NotAuthorized' })`), `core/auth/jwt.ts:36-39` (`hasCoachOrAdminRole`).

## Shared Patterns

### Error envelope
**Source:** `API/errors/responses.py` `build_error(code_int, "STATUS", msg)` via `HTTPException(detail=...)`; `auth/errors.py` `unauthenticated()` (line 52) is reusable for 401. Denials: `not_found(...)`/`EntityNotFoundException` for 404 (identical text), `build_error(403, "PERMISSION_DENIED", ...)` for 403.

### Dependency injection of repos
**Source:** `weight.py:45` `repo_dep = container_dep("weight")`; `repo: WeightRepository = Depends(repo_dep)`.

### Logging
Module `logger = logging.getLogger(__name__)`, lazy `%s`; log denials with principal id, module, op only (no tokens/emails).

### Module conventions
`from __future__ import annotations`, module docstring stating invariants, keyword-only collaborators, `Annotated`/`Depends` style as in principal.py.

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `API/authz/policy.py` table content | config | Only the ADR markdown exists; build Python dict mirroring `docs/adr/0007-authorization-policy-table.md` |
| Dev seed script (D-04) | script | No seeding script exists; use repository ports + RESEARCH Pitfall 11 (Study, Participant with `study_id`/`user_id`, participant User with `roles.participant.pid` + `verified_id`, coach `roles.coach.studies`, admin). Location is Claude's discretion |
| UAT checklist doc, ADR 0007 amendment (D-06/07/08/09, A1-A4) | docs | None |

## Metadata
**Analog search scope:** `backend/api/src/openwellness_api`, `backend/api/tests`, `frontend/mobile/feature/auth`, `frontend/dashboard/src/core/auth`, `frontend/dashboard/src/features/auth`
**Files read:** principal.py, v1.py, main.py, handlers.py, weight.py, token_service.py (partial), service.py (partial), conftest.py (partial), participant.py (partial), test_adr_policy_table.py, test_source_invariants.py (head), OpenWellnessAuthRepository.kt (partial), jwt.ts. Other routers, auth/errors.py details, and mobile error files relied on RESEARCH.md line cites and were not re-read.
**Pattern extraction date:** 2026-11-04
