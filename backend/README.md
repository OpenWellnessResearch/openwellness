# backend

The OpenWellness backend is a [uv](https://docs.astral.sh/uv/) workspace of
three Python packages that share one lockfile and one virtualenv. Two are
deployable services; one is the library they both build on.

| Package | Name | Role |
| --- | --- | --- |
| [`core/`](core/README.md) | `openwellness-core` | Shared library: domain models, repository ports, and Couchbase/Mongo adapters. No service entrypoint. |
| [`api/`](api/README.md) | `openwellness-api` | FastAPI service — the network source of truth for non-Python clients. |
| [`scheduler/`](scheduler/README.md) | `openwellness-scheduler` | Celery workers (and beat) for scheduled and background work. No HTTP layer. |

## Architecture

`core` is the hub. Both services depend on it and on nothing in each other —
they are siblings that meet only at the shared database.

```text
            ┌──────────────┐         ┌────────────────────┐
            │     api      │         │     scheduler      │
            │  (FastAPI)   │         │  (Celery workers)  │
            └──────┬───────┘         └─────────┬──────────┘
                   │                           │
                   │  import openwellness_core │
                   └─────────────┬─────────────┘
                                 ▼
                         ┌───────────────┐
                         │     core      │
                         | domain · ports|
                         |   adapters    |
                         └───────┬───────┘
                                 ▼
                  Couchbase / Sync Gateway · MongoDB
```

Every package follows **Clean Architecture**: source-code dependencies point
only inward, and the outer rings reach the inner ones through abstract
[ports](core/README.md#port). The shared vocabulary
([Entities](core/README.md#entities),
[Use Cases](core/README.md#use-cases),
[Interface Adapters](core/README.md#interface-adapters),
[Frameworks & Drivers](core/README.md#frameworks--drivers), the
[Dependency Rule](core/README.md#dependency-rule)) is defined once in the
[`core` glossary](core/README.md#glossary).

### How the pieces fit

- **`core`** owns the [domain](core/README.md#entities) and the repository
  [ports](core/README.md#port), plus their concrete Couchbase and Mongo
  [adapters](core/README.md#interface-adapters) and a
  `dependency-injector` composition root (`BaseContainer`). It is consumed by
  importing `openwellness_core`; it has no `main` of its own.

- **`api`** subclasses core's container as `ApplicationContainer`, supplies a
  concrete `AppConfig`, and exposes core entities as AIP-style REST resources
  under `/v1` (see `api/src/openwellness_api/resources/`). Its routes pull
  repositories straight from container providers — no hand-rolled state map.
  Entrypoint: `openwellness_api.main:app` (served by uvicorn), with a
  `/healthz` probe.

- **`scheduler`** subclasses core's container as `SchedulerContainer`, wraps
  use-case interactors in thin Celery tasks, and runs them in-process against
  the same datastores. Use cases depend only on core's repository ports — no
  Celery or DB imports leak inward.

Both services are packaged from the multi-stage [`Dockerfile`](Dockerfile)
(targets `api` and `scheduler`) and run together via the repository-root
`docker-compose.yml` (api, scheduler, and a Redis broker).

## Prerequisites

- **Python 3.12+** — every package targets `>=3.12`.
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running
  commands. All three packages are members of this one workspace, resolved
  from a single `uv.lock`.
- **Redis** — only the `scheduler` needs it, as the Celery broker/result
  backend. A local container is enough:
  `docker run -d --name redis -p 6379:6379 redis:7`.
- **Couchbase / Sync Gateway and MongoDB** — only needed at *runtime* by the
  services talking to live data. The test suites use in-memory fakes and need
  none of these (see [Testing](#testing)).

## Setup

Run everything from `backend/` (the workspace root) so the shared lockfile and
virtualenv are used. Pass `--extra dev` so the test and type-check tools
(`pytest`, `pyright`) land in the venv — a plain `uv sync` omits them and
`uv run pytest` then can't resolve the workspace packages:

```bash
cd backend
uv sync --extra dev
```

This installs all three packages as editable, so `import openwellness_core`
(and the service packages) work without a rebuild.

### Configuration

Services read settings from the environment. All settings live in a single
shared `.env` at the repository root, next to `docker-compose.yml` (start from
`.env.example`). Direct `uvicorn` / `celery` runs find it from any directory,
including `backend/`; set `OPENWELLNESS_ENV_FILE` to an absolute path to use a
different file. Precedence is: real environment variables, then `.env`, then
code defaults.

The `.env` holds direct-run values (`localhost`). `docker-compose.yml` overrides
`REDIS_URL` (api) and `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (scheduler)
with the compose `redis` service, so the same file works under compose. The
Couchbase, Sync Gateway, Mongo, and Redis variables are common to both
services; the `scheduler` additionally reads the `CELERY_*` variables.

**Migration:**

- If you keep an env file under `backend/`, move it to the repository root; it
  is no longer read.
- If your repo-root `.env` was copied from the old `.env.example`, it still has
  these lines, which a direct `uvicorn` or `celery` run cannot reach:

  ```sh
  CELERY_BROKER_URL=redis://redis:6379/0
  CELERY_RESULT_BACKEND=redis://redis:6379/1
  ```

  Change them to `redis://localhost:6379/0` and `redis://localhost:6379/1`
  (compose overrides both either way). Likewise change a `MONGO_URL` naming
  `host.docker.internal` to `localhost` for direct runs.

| Variable | Default | Purpose |
| --- | --- | --- |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for OTP codes and rate limits (api). |
| `POSTGRES_URL` | empty | Postgres connection string; read by core settings, used once the Postgres backend lands. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Message broker the worker pulls tasks from. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Where task results are stored. |
| `CELERY_TASK_DEFAULT_QUEUE` | `openwellness` | Default queue name for tasks. |
| `CELERY_TIMEZONE` | `UTC` | Timezone used by beat schedules. |
| `COUCHBASE_URL` | `couchbase://localhost` | Couchbase cluster the repositories connect to. |
| `COUCHBASE_USERNAME` | `Administrator` | Couchbase auth user. |
| `COUCHBASE_PASSWORD` | `password` | Couchbase auth password. |
| `COUCHBASE_BUCKET_NAME` | `openwellness` | Couchbase bucket holding the domain data. |
| `SYNC_GATEWAY_URL` | `http://localhost:4984/openwellness` | Sync Gateway endpoint. |
| `MONGO_URL` | `mongodb://localhost:27017` | Mongo connection string. |
| `MONGO_DB` | `openwellness` | Mongo database name. |

Example repo-root `.env`:

```sh
# Redis (api) and Celery broker / result backend
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

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

### Running the services

```bash
# api — http://localhost:8000 (/healthz, /v1)
uv run uvicorn openwellness_api.main:app --reload

# scheduler — a Celery worker (needs Redis running)
uv run celery -A openwellness_scheduler worker -l info
```

## Testing

**`pytest` cannot be run from this `backend/` level** — there is no aggregate
test target at the workspace root. Run the suite from within each package
instead (after `uv sync --extra dev` above):

```bash
cd backend/core      && uv run pytest   # mappers + N1QL parameterization
cd backend/api       && uv run pytest   # schemas, pagination, error mapping, CRUD
cd backend/scheduler && uv run pytest   # use cases + Celery task adapters
```

None of the suites require a live broker, Couchbase, or Mongo — they exercise
the code against in-memory fakes and stub settings. See each package's README
for what its tests cover:
[core](core/README.md#testing) ·
[api](api/README.md) ·
[scheduler](scheduler/README.md#testing).

Type-checking uses pyright (config in `pyrightconfig.json`) and *does* run from
the workspace root:

```bash
cd backend
uv run pyright
```
