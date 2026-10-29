# Coding Conventions

**Analysis Date:** 2026-10-29

## Naming Patterns

**Files (Python, `backend/**`):**
- Modules are `snake_case.py`: `backend/api/src/openwellness_api/auth/otp_store.py`, `backend/core/src/openwellness_core/adapters/couchbase/repositories/cb_weight_repository.py`.
- Repository ports end in `_repository.py` under `application/repositories/`; adapters are prefixed by backend: `cb_*` (Couchbase) in `adapters/couchbase/repositories/`, `mongo_*` in `adapters/mongo/repositories/`.
- Resource modules are singular nouns: `backend/api/src/openwellness_api/resources/user.py` (router), `backend/api/src/openwellness_api/schemas/user.py` (wire schemas), `backend/core/src/openwellness_core/domain/models/user.py` (entity).
- Private helper modules are underscore-prefixed: `backend/core/src/openwellness_core/adapters/couchbase/repositories/_query_helpers.py`, `backend/api/src/openwellness_api/schemas/_base.py`.

**Files (TypeScript, `frontend/dashboard/src/**`):**
- React components are `PascalCase.tsx`: `frontend/dashboard/src/core/ui/LoadingButton.tsx`, `frontend/dashboard/src/features/auth/ui/EmailStep.tsx`.
- Hooks are `useCamelCase.ts`: `frontend/dashboard/src/features/auth/hooks/useLogin.ts`.
- Non-component modules are `camelCase.ts`: `frontend/dashboard/src/core/api/apiClient.ts`, `frontend/dashboard/src/core/auth/tokenStorage.ts`, `frontend/dashboard/src/core/result.ts`.
- Feature sub-layers use lowercase-plural-free folder names: `api/`, `model/`, `hooks/`, `ui/` under `frontend/dashboard/src/features/<feature>/`.
- Test files are co-located and suffixed `.test.ts` / `.test.tsx`: `frontend/dashboard/src/core/api/apiClient.test.ts`. Cross-cutting tests live in `frontend/dashboard/src/test/integration/` (e.g. `loginFlow.test.tsx`).

**Functions (Python):**
- `snake_case` for functions and methods; private helpers use a leading underscore: `_normalize_email`, `_generate_code`, `_client_ip` (`backend/api/src/openwellness_api/auth/service.py`, `backend/api/src/openwellness_api/auth/router.py`).
- Router factories are named `build_router()` and return an `APIRouter`: `backend/api/src/openwellness_api/resources/user.py`, `backend/api/src/openwellness_api/auth/router.py`.
- Route handler functions are short verbs matching the resource action: `create`, `get`, `list_items`, `patch`, `delete` (inside `build_router`).

**Functions (TypeScript):**
- `camelCase` for functions: `dataErrorToAuthError`, `sendLoginCode`, `refreshSession`, `parseRetryAfterSeconds` (`frontend/dashboard/src/features/auth/api/authApi.ts`, `frontend/dashboard/src/core/errors.ts`).
- React components are named functions with `PascalCase`, exported by name (`export function EmailStep(...)`, `function Button(...)`). The only default export in `src/` is `frontend/dashboard/src/app/App.tsx`; prefer named exports.
- Hooks start with `use`: `useLogin`, `useSendLoginCode`, `useVerifyLoginCode` (`frontend/dashboard/src/features/auth/api/mutations.ts`).

**Variables and constants:**
- Python module-level constants are `UPPER_SNAKE_CASE`: `PURPOSE_LOGIN`, `UNIFORM_SEND_MESSAGE`, `SCHEMA_CONFIG`, `_COLLECTION` (`backend/api/src/openwellness_api/auth/errors.py`, `backend/api/src/openwellness_api/schemas/_base.py`). Module-level collection names are `_COLLECTION = "users"` (`backend/api/src/openwellness_api/resources/user.py`).
- TypeScript module constants: `UPPER_SNAKE_CASE` for fixtures and literals (`INITIAL_STATE`, `REFRESH_PATH`, `TOKEN_BODY` in tests); local variables are `camelCase`.
- Python logger is always the module logger: `logger = logging.getLogger(__name__)` (6 modules, e.g. `backend/api/src/openwellness_api/auth/service.py`).

**Types (Python):**
- Classes are `PascalCase`. Persistence models carry a `CB`/`Mongo` prefix: `CBWeight`, `CBUser` (`backend/core/src/openwellness_core/adapters/couchbase/model/`), `MongoUser` (`backend/core/src/openwellness_core/adapters/mongo/model/`).
- Wire schemas are plain nouns with request/response suffixes: `User`, `UserCreate`, `UserUpdate`, `UserList` (`backend/api/src/openwellness_api/schemas/user.py`).
- Result/value carriers are `@dataclass(frozen=True)`: `SendOutcome`, `Credential`, `RefreshedCredential` (`backend/api/src/openwellness_api/auth/service.py`).
- Exceptions end in `Exception` (domain/application) or `Error`/`NotFound`/`Invalid*` naming: `EntityNotFoundException` (`backend/core/src/openwellness_core/domain/exceptions/domain_exception.py`), `LimitExceededException`, `InvalidOtp`.

**Types (TypeScript):**
- `interface` for props and object shapes (`EmailStepProps`, `LoginState`, `LoginActions`, `RequestOptions`), `type` for unions and discriminated results (`Result<T, E>`, `AuthError`, `DataError`) in `frontend/dashboard/src/core/result.ts` and `frontend/dashboard/src/features/auth/model/errors.ts`.
- Props types are named `<Component>Props` and declared directly above the component (`frontend/dashboard/src/features/auth/ui/EmailStep.tsx`).
- Wire DTOs are suffixed `Dto` and live in `dtos.ts` next to the API layer: `TokenResponseDto`, `SendLoginCodeRequestDto` (`frontend/dashboard/src/features/auth/api/dtos.ts`).

**Wire naming:**
- Python attributes stay `snake_case`; wire JSON is `camelCase` via Pydantic `alias_generator=to_camel`. Configure this only through `SCHEMA_CONFIG` from `backend/api/src/openwellness_api/schemas/_base.py`:
  ```python
  from ._base import SCHEMA_CONFIG, ResourceBase

  class UserCreate(BaseModel):
      model_config = SCHEMA_CONFIG
      email: str
      is_active: bool
  ```
- Resource names follow AIP style `collection/{id}` (e.g. `users/abc`), and custom methods use the `:verb` suffix in URLs (`/v1/auth:sendLoginCode`, `/v1/users/{id}:undelete`). Mirror this in TypeScript with `buildApiUrl` (`frontend/dashboard/src/core/api/url.ts`) rather than hand-concatenating URLs.

## Code Style

**Python formatting:**
- No formatter or linter config is committed for Python (no `ruff`, `black`, or `.pre-commit-config.yaml` in `backend/`). The observed style is Black-compatible with ~88-column lines; follow it by hand.
- Trailing commas on multi-line call arguments and signatures; one argument per line when wrapping.
- Type hints are used throughout, including return types. Pyright is the checker, configured in `backend/pyrightconfig.json` (`pythonVersion` 3.12). Several rules are downgraded to `warning` there.

**Python future annotations:**
- New modules in `backend/api/src` and `backend/core/src` that use forward references start with `from __future__ import annotations`. About 30% of source modules do (101 of 338 files under `api/src`, `core/src`, `scheduler/src`); follow it in any module with non-trivial annotations, especially in `schemas/` and `resources/`.

**Python `# type: ignore` / `# noqa`:**
- Use the narrow form with a rule code and a reason comment: `# type: ignore[import-untyped]`, `# type: ignore[misc, assignment]` (`backend/api/src/openwellness_api/schemas/_base.py`). Do not add bare `# type: ignore`.

**TypeScript formatting (Prettier):**
- Config: `frontend/dashboard/prettier.config.js`.
  - `semi: false` (no semicolons)
  - `singleQuote: true`
  - Tailwind class sorting via `prettier-plugin-tailwindcss` with `tailwindStylesheet: './src/styles/globals.css'`
- Run `npm run format` (writes) or `npm run format:check` (CI). Prettier's default print width (80) applies; wrap JSX props and long unions the way Prettier does.
- Trailing commas are used in multi-line parameter lists and object literals (Prettier default `trailingComma: "all"`).

**TypeScript strictness:**
- `frontend/dashboard/tsconfig.app.json` enables `noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly`, `verbatimModuleSyntax`, and `noFallthroughCasesInSwitch`.
- Use `import type { ... }` for type-only imports (required by `verbatimModuleSyntax`): `import type { DataError } from '@/core/errors'` (`frontend/dashboard/src/features/auth/api/authApi.ts`).
- Path alias `@/*` maps to `frontend/dashboard/src/*`. Use it for cross-folder imports; relative imports (`./`, `../`) are used only within a feature folder or inside `core/api` and `core/auth`.
- Avoid `any`. The codebase currently has no `eslint-disable`, `@ts-ignore`, or `@ts-expect-error` escapes in `src/`; keep it that way.

**Linting (TypeScript):**
- ESLint flat config: `frontend/dashboard/eslint.config.js`.
  - `js.configs.recommended`, `tseslint.configs.recommended`, `reactHooks.configs.flat.recommended`, `reactRefresh.configs.vite`.
  - `react-refresh/only-export-components` is disabled only for `src/core/ui/**/*.tsx` (shadcn primitives export cva variants) and `src/core/auth/AuthContext.tsx`.
- Run with `npm run lint`.

**Layer boundaries (enforced by ESLint):**
- `src/core/` must not import from `src/features/`, `src/app/`, or `src/pages/` (`import-x/no-restricted-paths`).
- Within `src/features/auth/`:
  - `model/` must not import `api/`, `hooks/`, or `ui/`.
  - `api/` must not import `hooks/` or `ui/`.
  - `model/` and `api/` must stay React-free (`no-restricted-imports` on `react`, `react-dom`). The single exception is `src/features/*/api/mutations.ts`, the only file allowed to import `@tanstack/react-query`.
- Dependency direction: `ui/hooks → model ← api`.

**Backend layering (Clean Architecture, per `CONTRIBUTING.md`):**
- Dependencies point inward: `openwellness_core.domain` ← `openwellness_core.application` ← `openwellness_core.adapters` and `openwellness_api` / `openwellness_scheduler`.
- Outer rings reach inner ones through abstract ports, e.g. `openwellness_core.application.repositories.UserRepository` (`backend/core/src/openwellness_core/application/repositories/user_repository.py`) implemented by `openwellness_core.adapters.mongo.repositories.mongo_user_repository` (Mongo) or `openwellness_core.adapters.couchbase.repositories.cb_weight_repository` (Couchbase, shown for the pattern).
- Keep framework and datastore imports (`fastapi`, `redis`, `pymongo`, `couchbase`, `celery`) out of `domain/` and `application/`.

## Import Organization

**Python order (observed):**
1. `from __future__ import annotations`
2. Standard library (`import logging`, `import secrets`, `from dataclasses import dataclass`)
3. Third-party (`from fastapi import APIRouter`, `from pydantic import BaseModel`)
4. First-party workspace packages (`from openwellness_core...`, `from openwellness_api...`)
5. Relative imports within a package (`from ..common.handlers import ...`, `from .schemas import ...`)

Relative imports are used within a package (`openwellness_api`); absolute `openwellness_api.` / `openwellness_core.` imports are used across packages and in tests.

**TypeScript order (observed in `authApi.ts`, `useLogin.ts`):**
1. Side-effect or framework imports (`react`, `react-router-dom`, `vitest`, `@testing-library/*`)
2. Project alias imports `@/core/...`, `@/features/...`
3. Relative imports (`./authApi`, `./dtos`)
4. Type-only imports (`import type ...`) grouped with their source module

Separate groups with a blank line; do not reorder across groups.

**Path Aliases:**
- `@/` → `frontend/dashboard/src/` (defined in `frontend/dashboard/vite.config.ts` and `frontend/dashboard/tsconfig.app.json`). Vitest uses the same alias via the Vite config.

**Barrel files:**
- Python packages expose their public surface through `__init__.py` re-exports: `openwellness_core.application.repositories` re-exports every port (`from openwellness_core.application.repositories import UserRepository, ParticipantRepository, ...` is used in `backend/api/tests/conftest.py`). Add new ports to the package `__init__.py`.
- TypeScript does not use barrel `index.ts` files; import from the specific module.

## Error Handling

**Python (API boundary):**
- Domain and adapter errors are mapped to AIP-193 error envelopes in one place: `backend/api/src/openwellness_api/errors/handlers.py` (`register_exception_handlers`). Routers do not catch these; they let them propagate.
- Build error bodies with `build_error(code, status, message)` from `backend/api/src/openwellness_api/errors/responses.py`. Do not hand-build error dicts.
- Raise `fastapi.HTTPException` with `detail=build_error(...)` for route-level errors (`backend/api/src/openwellness_api/auth/errors.py`):
  ```python
  def invalid_code() -> HTTPException:
      return HTTPException(
          status_code=400,
          detail=build_error(400, "INVALID_ARGUMENT", _INVALID_CODE_MESSAGE),
      )
  ```
- For not-found in resource routers, call the helper `not_found(_COLLECTION, id_)` from `backend/api/src/openwellness_api/common/handlers.py` rather than raising directly.
- Domain exceptions inherit from `DomainException` (`backend/core/src/openwellness_core/domain/exceptions/domain_exception.py`), and `EntityNotFoundException` / `NotFound` map to 404.
- Auth responses are anti-enumeration: every send returns the same 200 body (`UNIFORM_SEND_MESSAGE`), and every verify failure returns the same 400 (`invalid_code()`). Never add an error message that reveals whether an account exists.
- Log unexpected server-side conditions with `logger.error("...: expected=%s actual=%s", ...)` (lazy `%s` formatting), not f-strings: `backend/api/src/openwellness_api/errors/handlers.py`.

**Python (core/adapters):**
- Adapters raise `openwellness_core.adapters.exceptions` types; application code depends on the port's documented exceptions, not on the driver's.
- Redis failures surface as `redis.exceptions.RedisError` and are mapped at the API layer.

**TypeScript (typed Result, no thrown HTTP errors):**
- Network and HTTP operations return `Result<T, E>` / `EmptyResult<E>` from `frontend/dashboard/src/core/result.ts`. Always branch on `.ok`; do not wrap calls in try/catch for HTTP failures.
  ```ts
  const result = await request<TokenResponseDto>('auth:verifyLoginCode', {
    method: 'POST',
    body,
  })
  return mapErr(map(result, toAuthSession), dataErrorToAuthError)
  ```
- Transport errors are `DataError` (`frontend/dashboard/src/core/errors.ts`), mapped to feature errors at the API boundary with an exhaustive `switch` on `kind` and a `default` fallback to `{ kind: 'Unknown' }` (`frontend/dashboard/src/features/auth/api/authApi.ts`).
- Feature error unions are discriminated on `kind` (`AuthError` in `frontend/dashboard/src/features/auth/model/errors.ts`). Render user-facing text through `authErrorMessage` in `frontend/dashboard/src/features/auth/model/messages.ts`; do not inline strings in components.
- Token refresh is single-flight in `frontend/dashboard/src/core/api/apiClient.ts`. Callers never implement their own retry on 401.

## Logging

**Backend (Python):**
- Framework: standard library `logging`. Every module that logs does `logger = logging.getLogger(__name__)` at module scope.
- Use `%`-style placeholders with arguments; never log secrets, OTP codes, tokens, or raw emails. `backend/api/src/openwellness_api/auth/service.py` documents that the OTP code is never logged.
- Use `logger.error` for unexpected states that produce a 5xx; use `logger.warning` or `logger.info` for expected business events.
- Do not use `print()` in application code. Current exceptions to avoid copying: `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py` lines 64-68 print exception details to stdout. Use `logger.exception(...)` instead.
- `print()` is acceptable only in standalone scripts such as `backend/core/scripts/check_no_fstring_n1ql.py`.

**Frontend (TypeScript):**
- No logging framework. Surface failures through typed `Result`/`AuthError` values and the UI state machine. Do not add `console.log` to committed code.

## Comments and Documentation

**Python docstrings:**
- Every module begins with a docstring describing its responsibility and invariants. Examples: `backend/api/src/openwellness_api/auth/service.py` (numbered security invariants), `backend/api/src/openwellness_api/auth/router.py` (why the router is thin).
- Public classes and functions have one-line or short multi-paragraph docstrings. Use triple double-quoted strings.
- Reference the mobile source when porting behavior, following the existing pattern: `"""Mirrors AuthError.kt ..."""` in `frontend/dashboard/src/features/auth/model/errors.ts`.

**TypeScript comments:**
- File headers are `//` comment blocks stating the mobile counterpart being mirrored (e.g. `// Mirrors LoginViewModel.kt + LoginContract.kt` in `frontend/dashboard/src/features/auth/hooks/useLogin.ts`). Keep this pattern when porting from `frontend/mobile`.
- Use JSDoc `/** ... */` on exported functions and interface members whose behavior is not obvious (see `frontend/dashboard/src/core/api/apiClient.ts`).
- Explain *why* in comments (anti-enumeration, single-flight, recursion guard), not *what*.

**When to comment:**
- Security-sensitive branches (anti-enumeration, constant-time comparison, CSPRNG use).
- Workarounds for framework or import cycles (e.g. the lazy import in `build_router()` in `backend/api/src/openwellness_api/auth/router.py`).
- Divergence from the mobile implementation.

## Function Design

**Size:** Route handlers and service methods are short; the router is intentionally thin and delegates to `AuthService` (`backend/api/src/openwellness_api/auth/router.py`). Put flow logic in service/use-case classes, not in route functions.

**Parameters (Python):**
- Keyword-only parameters for collaborators and options: `AuthService.__init__(self, *, settings, otp_store, ...)`, `RedisOtpStore(..., redis=..., clock=...)`.
- Dependency injection uses `dependency-injector` providers and FastAPI `Depends`: `repo: UserRepository = Depends(repo_dep)` (`backend/api/src/openwellness_api/resources/user.py`).
- Clocks are injected as `Callable[[], datetime]` so time is deterministic in tests.

**Parameters (TypeScript):**
- Prefer a single options object for optional config (`RequestOptions` in `frontend/dashboard/src/core/api/apiClient.ts`).
- Event handlers are named `on<Event>` in prop and action interfaces: `onEmailChange`, `onSendCodeClick`, `onErrorDismiss` (`frontend/dashboard/src/features/auth/ui/EmailStep.tsx`).

**Return Values:**
- Python services return frozen dataclasses (`SendOutcome`, `Credential`) and raise on failure.
- TypeScript returns `Result`/`EmptyResult` (`ok(...)`, `err(...)`, `okVoid()` from `frontend/dashboard/src/core/result.ts`) instead of throwing.

## Module Design

**Exports (Python):**
- Expose the module's public API via `__init__.py` re-exports. Keep helpers underscore-prefixed (`_ttl_or`, `_MAX_VERIFY_RETRIES`) and import them explicitly in tests only when needed.
- Factories (`build_router`, `container_dep("user")`) are the composition point; routers are not instantiated at import time.

**Exports (TypeScript):**
- Named exports only, except `App` in `frontend/dashboard/src/app/App.tsx`.
- Keep `model/` pure: types, validators, error mapping, and message catalogs with no React imports.

**Barrel Files:**
- Python: yes (`__init__.py` re-exports, see `openwellness_core.application.repositories`).
- TypeScript: no barrels. Import the concrete module path.

**Styling (dashboard):**
- Tailwind CSS v4 utility classes, composed with the `cn()` helper from `frontend/dashboard/src/core/lib/cn.ts` (`clsx` + `tailwind-merge`).
- Component variants use `class-variance-authority` `cva` (`frontend/dashboard/src/core/ui/button.tsx`). Add new variants there rather than conditional class strings.

## Where Conventions Are Not Yet Uniform

- Python formatting is not tool-enforced; reviewers should check line length and import grouping manually.
- Some Python modules omit `from __future__ import annotations` (about 70% of files). Add it to any new module that uses forward references.
- The `print()` calls in `mongo_base_repository.py` predate the logging convention; do not replicate them.

---

*Convention analysis: 2026-10-29*
