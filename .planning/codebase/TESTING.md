# Testing Patterns

**Analysis Date:** 2026-10-29

Testing spans two toolchains: Python (`backend/core`, `backend/api`, `backend/scheduler`) and TypeScript (`frontend/dashboard`). Every suite runs against in-memory fakes; no test needs a live Couchbase, MongoDB, Redis, Celery broker, or backend (per `CONTRIBUTING.md`).

## Test Framework

**Python runner:**
- pytest `>=8` declared in the `dev` extra of each package: `backend/core/pyproject.toml`, `backend/api/pyproject.toml`, `backend/scheduler/pyproject.toml`.
- No `pytest.ini`, `[tool.pytest.ini_options]`, or `setup.cfg` is committed. Defaults apply; discovery uses `test_*.py` under each package's `tests/` directory.
- Type checking: pyright (`backend/pyrightconfig.json`), run from the `backend/` root.

**Python assertion/support libraries:**
- Plain `assert` statements (pytest rewriting).
- `fakeredis` for Redis (`backend/api/tests/test_otp_store.py`, `backend/api/tests/test_auth_service.py`). Real Redis commands, including WATCH/MULTI, are exercised, not mocked.
- `mongomock` for MongoDB (`backend/api/tests/test_auth_service.py`).
- `fastapi.testclient.TestClient` for HTTP-level tests (`backend/api/tests/conftest.py`).
- `time-machine` is declared in `backend/api/pyproject.toml` dev extra for clock control.
- `httpx` is declared as a dev dependency for FastAPI client use.

**TypeScript runner:**
- Vitest `^4.1.8` with jsdom (`frontend/dashboard/vite.config.ts`, `test.environment: 'jsdom'`).
- Setup file: `frontend/dashboard/src/test/setup.ts`. It loads `@testing-library/jest-dom/vitest` and registers RTL `cleanup` in `afterEach` (globals are off; imports are explicit).
- Assertion library: Vitest `expect` extended by `@testing-library/jest-dom` matchers (`toBeInTheDocument`, `toBeDisabled`, `toHaveAttribute`).
- User interaction: `@testing-library/user-event` `^14.6.1` (`await userEvent.click(...)`).
- Network mocking: MSW `^2.14.6` (`msw/node`), with `frontend/dashboard/src/test/msw/server.ts` and `frontend/dashboard/src/test/msw/handlers.ts`.

**Run Commands:**
```bash
# Backend (run per package; there is no aggregate pytest target)
cd backend/core       && uv run pytest              # core suite
cd backend/api        && uv run pytest              # api suite
cd backend/scheduler  && uv run pytest              # scheduler suite
cd backend/api        && uv run pytest api/tests/test_otp_store.py   # single file
cd backend            && uv run pyright             # type-check (workspace root)

# Dashboard (run from frontend/dashboard)
npm run test                                        # vitest run (single pass)
npm run test:watch                                  # vitest (watch mode)
npm run typecheck                                   # tsc -b
npm run lint                                        # eslint . (includes layer rules)
npx vitest run src/features/auth/api/authApi.test.ts  # single file
```

- Install prerequisites: `cd backend && uv sync --extra dev` (a plain `uv sync` omits pytest and pyright). `cd frontend/dashboard && npm install`.
- No coverage script is defined in either toolchain. There is no `--cov` configuration and no `vitest --coverage` provider in `frontend/dashboard/package.json`.

## Test File Organization

**Python location:**
- Separate `tests/` directory per package, not co-located with source:
  - `backend/core/tests/` (3 files: `test_smoke.py`, `test_repositories_queries.py`, `test_user_verified_id.py`)
  - `backend/api/tests/` (16 files, listed below)
  - `backend/scheduler/tests/` (2 files: `test_tasks.py`, `test_count_study_participants.py`)
- Each `tests/` has `__init__.py` (or is package-marked) and a `conftest.py` for shared fakes and fixtures:
  - `backend/api/tests/conftest.py`
  - `backend/scheduler/tests/conftest.py`

**Python naming:**
- File: `test_<subject>.py`, e.g. `test_otp_store.py`, `test_users_crud.py`, `test_weights_owner_crud.py`.
- Function: `test_<behavior>` in snake_case, e.g. `test_user_crud_flow`, `test_user_404_envelope`, `test_paginate_emits_token_only_when_more_remain` (`backend/api/tests/test_pagination.py`).
- Docstrings at the top of each file state the scope and invariants under test (see `backend/core/tests/test_smoke.py`, `backend/api/tests/test_otp_store.py`).

**Python API test files (`backend/api/tests/`):**
- `test_auth_api.py`, `test_auth_container.py`, `test_auth_router_smoke.py`, `test_auth_service.py`
- `test_email_sender.py`, `test_error_mapping.py`, `test_filter.py`, `test_goals_carveout.py`
- `test_otp_store.py`, `test_pagination.py`, `test_principal.py`, `test_schemas.py`
- `test_session_store.py`, `test_token_service.py`, `test_users_crud.py`, `test_weights_owner_crud.py`

**TypeScript location:**
- Unit tests are co-located with the module under test:
  - `frontend/dashboard/src/core/errors.test.ts` next to `frontend/dashboard/src/core/errors.ts`
  - `frontend/dashboard/src/core/api/apiClient.test.ts`, `url.test.ts`
  - `frontend/dashboard/src/core/auth/AuthContext.test.tsx`, `jwt.test.ts`, `tokenStorage.test.ts`
  - `frontend/dashboard/src/core/ui/LoadingButton.test.tsx`, `EmailField.test.tsx`, `OtpInput.test.tsx`
  - `frontend/dashboard/src/features/auth/api/authApi.test.ts`, `api/mappers.test.ts`
  - `frontend/dashboard/src/features/auth/model/validators.test.ts`, `model/messages.test.ts`
  - `frontend/dashboard/src/features/auth/hooks/useLogin.test.tsx`
  - `frontend/dashboard/src/app/App.test.tsx`
- Cross-feature integration tests live in `frontend/dashboard/src/test/integration/` (e.g. `loginFlow.test.tsx`).
- Shared helpers live in `frontend/dashboard/src/test/` (`jwt.ts`, `msw/handlers.ts`, `msw/server.ts`, `setup.ts`). Do not put test helpers under `src/core` or `src/features`.

**TypeScript naming:**
- `<moduleName>.test.ts(x)` matching the module, e.g. `authApi.test.ts` for `authApi.ts`, `LoadingButton.test.tsx` for `LoadingButton.tsx`.
- Test names are sentences in the `describe` / `it` form, starting with a verb: `it('renders as disabled and aria-busy when loading')`, `it('maps each known status to its kind')`.

**Structure:**
```
backend/api/tests/
├── __init__.py
├── conftest.py                # in-memory fakes, app/client fixtures, env stubs
├── test_<subject>.py          # one module per subject

frontend/dashboard/src/
├── core/errors.ts
├── core/errors.test.ts        # co-located unit test
└── test/
    ├── setup.ts               # global jest-dom + RTL cleanup
    ├── jwt.ts                 # fakeJwt() builder
    ├── msw/handlers.ts        # happy-path MSW handlers
    ├── msw/server.ts          # setupServer(...defaultHandlers)
    └── integration/loginFlow.test.tsx
```

## Test Structure

**Python suite organization (function style, module-level tests):**
```python
"""Happy-path CRUD for the top-level Users resource (AIP wire format)."""


def test_user_404_envelope(client) -> None:
    r = client.get("/v1/users/does-not-exist")
    assert r.status_code == 404
```
- Tests are plain functions with `-> None` return annotations. Classes (`class Test...`) are used sparingly; 5 class-based groups exist across the backend suites, so prefer functions for new tests.
- Fixtures are injected by name: `client`, `app`, `fakes`, `fake_email_sender`, `seed_accounts` (`backend/api/tests/conftest.py`).
- Use helper factories prefixed with `_` for construction: `_settings(**overrides)`, `_store(...)` in `backend/api/tests/test_otp_store.py`. Accept `**overrides` so each test changes only the field under test.
- Use fixed clocks: `FIXED_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)` and inject `clock=lambda: FIXED_NOW` (`backend/api/tests/test_otp_store.py`).
- Set environment before importing app code. `conftest.py` calls `os.environ.setdefault(...)` for `COUCHBASE_URL`, `MONGO_URL`, `API_AUTH_JWT_SECRET`, `API_AUTH_CODE_PEPPER` before any `openwellness_api` import. Scheduler `conftest.py` does the same for `CELERY_BROKER_URL` (`memory://`) and `CELERY_RESULT_BACKEND`.

**Python `parametrize`:**
- Used sparingly, in a few modules such as `backend/api/tests/test_principal.py`, `backend/api/tests/test_token_service.py`, and `backend/api/tests/test_otp_store.py`. Use `@pytest.mark.parametrize` for table-style cases (for example, several invalid inputs that must all produce the same outcome); follow the existing usage in those files.

**TypeScript suite organization:**
```ts
// frontend/dashboard/src/core/errors.test.ts
describe('statusToNetworkError', () => {
  it('maps each known status to its kind', () => {
    expect(statusToNetworkError(400)).toBe('BAD_REQUEST')
  })

  it('falls back to UNKNOWN for unmapped statuses', () => {
    expect(statusToNetworkError(418)).toBe('UNKNOWN')
  })
})
```
- One top-level `describe` per exported function or component; nested `describe` only for sub-features.
- Test bodies use an explicit `expect` per behavior. Keep one behavior per `it`.
- Unit test files begin with a `//` comment naming the mobile counterpart they mirror (`// Tests for core/errors.ts (mirrors DataError.kt + ...)`). Keep this when adding tests for ported code.

**Patterns:**
- Setup: construct fresh fakes in each test or in a helper (`_store()`). Do not share mutable state across tests at module scope.
- Teardown: Python fakes are garbage-collected; no explicit teardown. TypeScript: `afterEach(cleanup)` is global in `setup.ts`. For fetch stubs, use `vi.stubGlobal` in `beforeEach` and `vi.unstubAllGlobals()` / `vi.restoreAllMocks()` in `afterEach` (see `authApi.test.ts`).
- Assertions: `assert r.status_code == 201, r.text` style (include the response body as the failure message on HTTP asserts).

## Mocking

**Python: prefer real fakes over `unittest.mock`:**
- Fake repositories are hand-written dict-backed classes that subclass the real port. `InMemoryBaseRepo` and `FakeUserRepo` in `backend/api/tests/conftest.py` implement `BaseCrudRepository`; `FakeParticipantRepo` in `backend/scheduler/tests/conftest.py` implements `ParticipantRepository`.
- Fake collaborators with a public test hook: `FakeEmailSender` in `backend/api/src/openwellness_api/auth/email_sender.py`. Read the OTP via `fake_email.last_code(email)`; the service never exposes it otherwise.
- Real in-memory backends: `fakeredis.FakeRedis(decode_responses=True)` and `mongomock` (`backend/api/tests/test_auth_service.py`).
- `monkeypatch` is used for environment and module attribute overrides (`backend/api/tests/test_auth_container.py`, `backend/api/tests/test_email_sender.py`).
- `unittest.mock` / `MagicMock` appear rarely. Do not introduce them for repositories or stores; add or extend a fake instead.

**Python dependency overrides:**
- FastAPI overrides for the container and auth service: `app.dependency_overrides[...] = ...` in the `app` fixture (`backend/api/tests/conftest.py`). Prefer this over patching modules.
- Repositories are injected through `RepositoryContainer` (`container_dep("user")`), so tests replace a single repo by building the fake map passed to the `fakes` fixture.

**TypeScript: MSW for HTTP, `vi` for functions:**
- Network: use MSW handlers that match the full absolute URL produced by `buildApiUrl`. Verbs with `:` need an anchored RegExp (see `frontend/dashboard/src/test/msw/handlers.ts`):
  ```ts
  // Exact-match URL matcher for a custom-method verb (e.g. auth:verifyLoginCode).
  // An anchored RegExp with the colon escaped so each verb matches ONLY its own URL.
  ```
- Per-test MSW server lifecycle is wired in each test file, not globally, so `setup.ts` stays light. Pattern:
  ```ts
  import { server } from '@/test/msw/server'
  beforeAll(() => server.listen())
  afterEach(() => server.resetHandlers())
  afterAll(() => server.close())
  ```
- Lighter tests stub `fetch` with `vi.stubGlobal('fetch', vi.fn(...))` and return `new Response(JSON.stringify(body), {...})` (see `frontend/dashboard/src/core/api/apiClient.test.ts`, `authApi.test.ts`).
- Function mocks: `vi.fn()` for callbacks and assertion via `toHaveBeenCalledTimes(1)` / `not.toHaveBeenCalled()` (`LoadingButton.test.tsx`).
- Auth tokens in tests are built with `fakeJwt({ sub, roles, participant })` from `frontend/dashboard/src/test/jwt.ts`. The app decodes payloads only (no signature verification), so placeholder signatures are fine. Do not copy inline JWT builders; import `fakeJwt`.

**What to Mock:**
- External I/O boundaries: HTTP (`fetch` / MSW), email sending (`FakeEmailSender`), Redis and Mongo (use the fakes above), Celery (use `memory://` broker).
- Persistence ports (repositories) via the in-memory fakes that subclass the port.
- Time: inject a `clock` callable (Python) or use fixed timestamps; `time-machine` is available for code that calls `datetime.now()` directly.

**What NOT to Mock:**
- Domain entities and value objects (construct real `Weight`, `User`, `Goal` instances).
- Pure functions in `model/` (validators, mappers, `result.ts` helpers). Test them directly.
- Redis and Mongo behavior: use `fakeredis` / `mongomock`, which exercise real command semantics (e.g. atomic OTP verify). Do not replace them with `MagicMock`.
- The Pydantic schemas and serialization round-trips (`backend/core/tests/test_smoke.py` round-trips through `from_domain` → `model_dump` → `model_validate` → `to_domain`).

## Fixtures and Factories

**Python fixtures (`backend/api/tests/conftest.py`):**
- `fakes` returns the `dict[type, Any]` of in-memory repositories keyed by port class.
- `fake_email_sender` returns the `FakeEmailSender` attached to the app's auth container.
- `app` builds the FastAPI app with overrides; `client` wraps it in `TestClient`.
- `seed_accounts` seeds users/participants and is opt-in. Request it only in tests that need pre-existing accounts; the default fixture set is empty.

**Python factories:**
```python
def _settings(**overrides: object) -> AuthSettings:
    base: dict[str, object] = {
        "code_pepper": "test-pepper",
        "otp_ttl_seconds": 600,
        "otp_max_attempts": 5,
        # ...
    }
    base.update(overrides)
    return AuthSettings(**base)  # type: ignore[arg-type]
```
- Build test data with domain constructors and owner IDs as plain strings: `Weight(owner="p1", study_id="s1", weight=180.5)` (`backend/core/tests/test_smoke.py`).

**TypeScript fixtures (`frontend/dashboard/src/test/`):**
- Response bodies are module-level `const` objects in the test file, named `*_BODY` or `ERROR_<status>` (e.g. `TOKEN_BODY`, `ERROR_429_WITH_SECS` in `authApi.test.ts`).
- Shared wire fixtures for the login flow live in `frontend/dashboard/src/test/msw/handlers.ts` (`coachToken`, `participantToken`).
- Helper builders in the test file: `jsonResponse(body, status, headers)` returns a real `Response`.

**Location:**
- Python: `backend/<pkg>/tests/conftest.py` for package-wide fixtures; per-file helpers stay in the test module.
- TypeScript: `frontend/dashboard/src/test/` for shared helpers; per-file helpers stay in the test file.

## Coverage

**Requirements:** None enforced. No coverage threshold appears in `backend/*/pyproject.toml` or `frontend/dashboard/package.json`, and no CI coverage gate is committed.

**View Coverage:**
- Not configured. To inspect coverage ad hoc, add the tooling temporarily:
  ```bash
  cd backend/api && uv run pytest --cov=openwellness_api   # requires pytest-cov, not in dev extra
  cd frontend/dashboard && npx vitest run --coverage        # requires @vitest/coverage-v8, not in devDependencies
  ```

## Test Types

**Unit tests:**
- Python: `backend/core/tests/test_smoke.py` (entity and DTO round-trips), `backend/api/tests/test_pagination.py`, `backend/api/tests/test_filter.py`, `backend/api/tests/test_token_service.py`.
- TypeScript: validators, mappers, error mapping, and UI primitives (`src/features/auth/model/validators.test.ts`, `src/features/auth/api/mappers.test.ts`, `src/core/ui/*.test.tsx`).

**Integration tests (in-process, still no live services):**
- Python API: `TestClient` drives the routers against in-memory fakes. Examples: `backend/api/tests/test_users_crud.py`, `backend/api/tests/test_weights_owner_crud.py`, `backend/api/tests/test_auth_api.py`.
- Python auth service: real `RedisOtpStore` over `fakeredis`, real `JwtTokenService`, `RefreshSessionStore` over `mongomock` (`backend/api/tests/test_auth_service.py`).
- Dashboard: `frontend/dashboard/src/test/integration/loginFlow.test.tsx` runs the login flow through the real hooks and API client with MSW handlers standing in for the backend.
- Scheduler: `backend/scheduler/tests/test_tasks.py` exercises Celery task adapters with the in-memory `FakeParticipantRepo`.

**E2E tests:**
- Not used. No Playwright, Cypress, or similar is configured for the dashboard.

## Common Patterns

**Async testing (Python):**
- Routes and services are sync `def` (the router docstring explains threadpool execution), so tests call them synchronously through `TestClient`. No `pytest-asyncio` is configured; do not write `async def` tests unless you add it.

**Async testing (TypeScript):**
```ts
it('resolves to a typed Result', async () => {
  const result = await sendLoginCode('a@b.com')
  expect(result.ok).toBe(true)
})
```
- `await` the call; assert on the resolved `Result` with `.ok` rather than expecting thrown errors.
- For UI state changes, use `await userEvent.click(...)` and `await screen.findByRole(...)` for async renders.

**Error testing (Python):**
```python
def test_user_404_envelope(client) -> None:
    r = client.get("/v1/users/does-not-exist")
    assert r.status_code == 404
```
- Assert the status code and, where the envelope matters, the AIP-193 body (`error.code`, `error.status`, `error.message`). Verify anti-enumeration by asserting the identical body for distinct failure causes (`backend/api/tests/test_auth_api.py`).
- Use `pytest.raises(SomeException)` for direct service/repository exceptions.

**Error testing (TypeScript):**
```ts
it('maps any other 5xx to SERVER_ERROR', () => {
  expect(statusToNetworkError(500)).toBe('SERVER_ERROR')
})
```
- Assert on the typed `Result` error (`result.ok === false`, `result.error.kind === '...'`) rather than exceptions.
- Use MSW to return the wire error envelope (`{ error: { code, status, message, details } }`) and assert the mapped `AuthError`.

**Redis/timing-sensitive tests (Python):**
- Use injected clocks and `fakeredis` TTL semantics. Do not `time.sleep()` in tests.

**Security invariant tests:**
- Several test files assert PII discipline and secrecy directly: no raw email in Redis keys, no plaintext code in stored hash records (`backend/api/tests/test_otp_store.py`). Add equivalent assertions when touching OTP, token, or email code paths.

## Adding New Tests

- **Backend resource:** add `backend/api/tests/test_<resource>_crud.py` following `test_users_crud.py`. Use the `client` fixture; add any new repo fake to `conftest.py` by subclassing `InMemoryBaseRepo`.
- **Backend use case:** add `backend/scheduler/tests/test_<use_case>.py` (or `backend/core/tests/`) and build the fake port inline in `conftest.py`.
- **Dashboard module:** co-locate `<module>.test.ts(x)` next to the source. Use `fakeJwt` for tokens and MSW handlers for HTTP. Name the test to the mobile counterpart when one exists.
- **Dashboard cross-feature flow:** add to `frontend/dashboard/src/test/integration/`.
- Run the relevant package suite plus `pyright` (backend) or `npm run lint && npm run typecheck && npm run test` (dashboard) before opening a PR.

---

*Testing analysis: 2026-10-29*
