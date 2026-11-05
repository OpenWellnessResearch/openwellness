# openwellness-api

`openwellness-api` — the FastAPI service. It is the network source of truth
for all non-Python clients (dashboard, mobile), exposing the
[`core`](../core/README.md) domain entities as AIP-style REST resources under
`/v1`.

It carries no business rules of its own: it is a delivery mechanism. Every
route resolves a repository [port](../core/README.md#port) from core, invokes
it, and translates between core's internal representation (epoch-float
timestamps, bare `id`) and the public wire format (RFC-3339 timestamps,
resource `name`). Depends on [`../core`](../core/README.md) for the domain
models, repository ports, and concrete Couchbase/Mongo adapters.

## Architecture

In Clean Architecture terms the service is the outer two rings — the
[Interface Adapters](../core/README.md#interface-adapters) and the
[Frameworks & Drivers](../core/README.md#frameworks--drivers) — wrapped around
core. The [Dependency Rule](../core/README.md#dependency-rule) still holds:
the routers depend inward on core's
[ports](../core/README.md#port) and never the reverse, and core knows nothing
about HTTP, FastAPI, or the wire schemas.

```text
        HTTP client (dashboard / mobile)
                    │
                    ▼
    ┌───────────────────────────────────────────┐
    │ openwellness_api                           │
    │   main · v1        app factory, /v1 router │
    │   resources/       FastAPI routers         │  ← controllers
    │   auth/            OTP login · JWT         │
    │   schemas/         request/response models │  ← wire DTOs
    │   common/          (de)serialization glue  │
    │   deps/            DI + principal           │
    │   errors/          exception → AIP-193      │
    │   config · container                        │
    └───────────────────┬─────────────────────────┘
                        │  import openwellness_core
                        ▼
                ┌───────────────┐
                │     core      │
                | domain · ports|
                |   adapters    |
                └───────┬───────┘
                        ▼
         Couchbase / Sync Gateway · MongoDB
```

### Layout

```text
src/openwellness_api/
├── main.py            # app factory, lifespan, /healthz, CORS
├── v1.py              # /v1 router aggregator
├── config.py          # AppConfig (implements core's AppConfigInterface) + APISettings
├── container.py       # ApplicationContainer — subclasses core's BaseContainer
├── resources/         # one FastAPI router module per entity (controllers)
├── auth/              # email-OTP + JWT auth: router, service, token/OTP/session stores, email sender
├── schemas/           # Pydantic request/response models (camelCase wire shape)
├── common/            # serialization, pagination, filter, time-range, resource-name helpers
├── deps/              # container-backed repo dependency + caller principal
└── errors/            # domain/adapter exceptions → AIP-193 HTTP responses
```

- **`resources/` — controllers.** Each module exposes a `build_router()`
  returning the routes for one entity. Routers pull their repository through
  `container_dep("<provider>")`, which resolves the matching provider on
  core's `RepositoryContainer` per request — so a test can override one
  provider and have live routes see it. [`weight.py`][weight] is the canonical
  owner-scoped reference (it spells out every method in full); `user.py` is
  the canonical top-level reference; sister modules mirror those skeletons.

- **`auth/` — the authentication slice.** Six `/v1/auth:*` custom methods —
  `sendLoginCode` / `verifyLoginCode`, `sendRegistrationCode` /
  `verifyRegistrationCode`, `refreshToken` / `revokeToken` — implementing
  email-OTP login that issues JWT access/refresh tokens. OTP codes and rate
  limits live in Redis, refresh sessions in Couchbase, and codes are
  delivered over SMTP. Configured via the `API_AUTH_*` settings.

- **`schemas/` — wire DTOs.** Pydantic v2 models for request bodies and
  responses. They inherit the AIP standard-field set (`name`, `createTime`,
  `updateTime`) and the shared [`SCHEMA_CONFIG`][base] (`camelCase` aliasing,
  `populate_by_name`, `extra="ignore"`), keeping the public shape independent
  of core's domain dataclasses.

- **`common/` — the boundary glue.** The helpers that convert between core's
  representation and the wire format: `handlers` (serialize/patch/audit),
  `pagination` (opaque cursor tokens), `filter` (the `filter=` subset),
  `time_range` (bounded-window validation), and `resource_name`
  (`collection/{id}` formatting).

- **`deps/` — FastAPI dependencies.** `container.container_dep` binds a route
  to a named repository provider. `principal.get_principal` verifies the
  `Authorization: Bearer` access token and returns the caller (roles,
  participant, coach studies); a missing or invalid token is a 401, with no
  fallback identity.

- **`authz/` — authorization.** `policy.POLICY` is the table mirroring
  [ADR 0007](../../docs/adr/0007-authorization-policy-table.md), and
  `engine.authorize(module, op)` is the dependency every resource route
  carries. On owner-scoped routes the `{user}` path segment holds a
  participant id, not a user id (ADR 0005).

- **`errors/` — error mapping.** `handlers.register_exception_handlers` maps
  core's domain and adapter exceptions (e.g.
  `EntityNotFoundException` → 404, `LimitExceededException` → 429) plus
  validation failures onto the AIP-193 error envelope built by `responses`.

- **`config.py` / `container.py` — composition.** `AppConfig` implements
  core's `AppConfigInterface` from environment-backed settings;
  `ApplicationContainer` subclasses core's `BaseContainer` purely to mark the
  API as the binding site for that config. `main.create_app()` builds the app,
  and the lifespan overrides `app_config`, opens the Couchbase connection, and
  wires the resource modules.

### API conventions (AIP)

The HTTP surface follows Google's [API Improvement Proposals][aip]:

| Aspect | Convention |
| --- | --- |
| Resource names | `collection/{id}`, or `parent/{pid}/collection/{id}` when nested (AIP-122). |
| Standard methods | `POST`/`GET`/`PATCH`/`DELETE` + the custom verbs `:undelete` and `:purge`. |
| Soft delete | `DELETE` archives (core `archive`); `:undelete` restores; `:purge` hard-deletes. |
| Field casing | `camelCase` on the wire, `snake_case` server-side (AIP-140). |
| Timestamps | RFC-3339 `createTime` / `updateTime` (AIP-148). |
| List responses | `{<plural>: [...], "nextPageToken": ...}` with opaque cursor tokens (AIP-132/158). |
| Filtering | `filter=field=value` clauses joined by `AND` — a documented subset of AIP-160. |
| Errors | The `{"error": {code, status, message, details}}` envelope (AIP-193). |

## Prerequisites

- **Python 3.12+** (the package targets `>=3.12`).
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running
  commands. `api` is a member of the `backend/` uv workspace and depends on
  `core` as a workspace package.
- **Couchbase / Sync Gateway, MongoDB, and Redis** are only needed at
  *runtime* when the service talks to live data (Redis backs the auth OTP and
  rate-limit stores). The test suite uses in-memory fakes and needs none of
  them (see [Testing](#testing)).

## Configuration

The service reads all settings from the environment. For local development,
put them in `backend/.env`. The datastore variables are the slice of
[`core`](../core/README.md)'s config interface the API forwards to the drivers;
the `API_*` variables are API-only knobs.

| Variable | Default | Purpose |
| --- | --- | --- |
| `COUCHBASE_URL` | `couchbase://localhost` | Couchbase cluster the repositories connect to. |
| `COUCHBASE_USERNAME` | `Administrator` | Couchbase auth user. |
| `COUCHBASE_PASSWORD` | `password` | Couchbase auth password. |
| `COUCHBASE_BUCKET_NAME` | `openwellness` | Couchbase bucket holding the domain data. |
| `SYNC_GATEWAY_URL` | `http://localhost:4984/openwellness` | Sync Gateway endpoint. |
| `MONGO_URL` | `mongodb://localhost:27017` | Mongo connection string. |
| `MONGO_DB` | `openwellness` | Mongo database name. |
| `API_TITLE` | `OpenWellness API` | OpenAPI title. |
| `API_ENABLE_DOCS` | `false` | Serve `/docs`, `/redoc` and `/openapi.json`. Leave off on a deployed instance. |
| `API_DEFAULT_PAGE_SIZE` | `50` | Page size used when a list request omits `page_size`. |
| `API_MAX_PAGE_SIZE` | `1000` | Upper bound on a requested `page_size`. |
| `API_TIME_RANGE_MAX_SPAN_DAYS` | `7` | Max window (days) for time-series list queries. |
| `API_CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed by CORS (dashboard SPA). |

Auth adds three more setting groups — `API_AUTH_*` (JWT secret/TTLs, OTP
length/TTL, rate limits), `REDIS_*` (OTP and
rate-limit store), and `SMTP_*` (login-code email delivery). See
[`config.py`](src/openwellness_api/config.py) for the full list and defaults.

Example `backend/.env`:

```sh
# Couchbase
COUCHBASE_URL=couchbase://localhost
COUCHBASE_USERNAME=Administrator
COUCHBASE_PASSWORD=password
COUCHBASE_BUCKET_NAME=openwellness

# Sync Gateway
SYNC_GATEWAY_URL=http://localhost:4984/openwellness

# Mongo
MONGO_URL=mongodb://localhost:27017
MONGO_DB=openwellness
```

## Setup

Run from the `backend/` workspace root so the shared `uv.lock` is used. Pass
`--extra dev` so the test and type-check tools (`pytest`, `pyright`,
`httpx`) land in the shared venv — a plain `uv sync` omits them, and
`uv run pytest` then fails to resolve `openwellness_api`:

```sh
cd backend
uv sync --extra dev
```

`api` and `core` install as editable packages, so imports resolve without a
rebuild.

## Running

Start the service with uvicorn (live datastores must be reachable):

```sh
# From backend/ — http://localhost:8000
uv run uvicorn openwellness_api.main:app --reload
```

Useful endpoints:

- `GET /healthz` — liveness probe (`{"status": "ok"}`).
- `GET /docs` — interactive OpenAPI docs (only when `API_ENABLE_DOCS` is on).
- `GET /v1/...` — the resource collections (e.g. `GET /v1/users`,
  `POST /v1/users/{user}/weights`).
- `POST /v1/auth:sendLoginCode` — start an email-OTP login.

## Testing

The tests drive the routers through FastAPI's `TestClient` against in-memory
fake repositories wired into an `ApplicationContainer` — no Couchbase, Mongo,
or live config is required. `conftest.py` seeds stub connection settings and
overrides each repository provider with a dict-backed fake, so the suite runs
with nothing else running:

```sh
# From backend/api
uv run pytest

# Or target this package from the workspace root
uv run pytest api
```

What the suite covers:

- `test_users_crud.py` / `test_weights_owner_crud.py` — happy-path CRUD for a
  top-level and an owner-scoped resource, asserting the AIP wire format
  (resource `name`, owner scoping, 404 on owner mismatch).
- `test_goals_carveout.py` — the Goal discriminated union round-tripped with
  the `filter=kind=N` query.
- `test_pagination.py` — cursor-token round-trip and page-size capping.
- `test_filter.py` — the `filter=` parser's accepted subset and its 400s.
- `test_error_mapping.py` — each core exception maps to the right AIP-193
  status.
- `test_schemas.py` — response models accept real-world-shaped documents.
- `test_auth_*.py`, `test_token_service.py`, `test_otp_store.py`,
  `test_session_store.py`, `test_email_sender.py`, `test_principal.py` — the
  OTP login/registration flow, JWT issue/refresh/revoke, and the principal
  fallback behaviour.

Type-checking uses pyright (config in `../pyrightconfig.json`):

```sh
cd backend
uv run pyright
```

[weight]: src/openwellness_api/resources/weight.py
[base]: src/openwellness_api/schemas/_base.py
[aip]: https://google.aip.dev/
