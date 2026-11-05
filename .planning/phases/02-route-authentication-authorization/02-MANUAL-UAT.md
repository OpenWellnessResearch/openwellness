# Phase 2 manual UAT: route authentication and authorization

Covers D-10, D-11, D-12 and D-13 for AUTH-09. The CI half of D-12 is `backend/api/tests/test_e2e_roles_flow.py`, which runs the same dev seed this document uses. This half runs the real clients against a live local API. It is for the developer to run and sign off; nothing here has been run yet.

## D-10 static check

D-10 replaced a logging-only observation pass with a recorded grep of every client call site. If any path other than `auth:*` appeared below, enforcement could break a client call and the plan would stop. None did.

Recorded at HEAD `0d94c53` on 2026-11-04. Commands run from the repository root; output is verbatim.

Dashboard request call sites (`request(` / `request<T>(`):

```
$ grep -rnE "request(<[^>]*>)?\(" frontend/dashboard/src --include='*.ts' --include='*.tsx' --exclude='*.test.*' --exclude-dir=test
frontend/dashboard/src/core/api/apiClient.ts:41:export async function request<T>(
frontend/dashboard/src/features/auth/api/authApi.ts:57:  const result = await request<UniformSendResponseDto>('auth:sendLoginCode', {
frontend/dashboard/src/features/auth/api/authApi.ts:69:  const result = await request<TokenResponseDto>('auth:verifyLoginCode', {
frontend/dashboard/src/features/auth/api/authApi.ts:95:  const result = await request<RevokeResponseDto>('auth:revokeToken', {
```

Dashboard `auth:` paths:

```
$ grep -rnE "'auth:" frontend/dashboard/src --include='*.ts' --exclude='*.test.*' --exclude-dir=test
frontend/dashboard/src/core/api/apiClient.ts:29:const REFRESH_PATH = 'auth:refreshToken'
frontend/dashboard/src/features/auth/api/authApi.ts:57:  const result = await request<UniformSendResponseDto>('auth:sendLoginCode', {
frontend/dashboard/src/features/auth/api/authApi.ts:69:  const result = await request<TokenResponseDto>('auth:verifyLoginCode', {
frontend/dashboard/src/features/auth/api/authApi.ts:95:  const result = await request<RevokeResponseDto>('auth:revokeToken', {
```

Mobile call sites:

```
$ grep -rnE 'execute\(|"auth:|appendPathSegments\(' frontend/mobile --include='*.kt' --exclude-dir=build --exclude-dir=androidHostTest
frontend/mobile/core/data/src/commonMain/kotlin/edu/openwellness/mobile/core/data/network/HttpClientFactory.kt:80:                            appendPathSegments("auth:refreshToken")
frontend/mobile/core/data/src/commonMain/kotlin/edu/openwellness/mobile/core/data/network/HttpClientExt.kt:42:        execute()
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:45:        execute("auth:sendLoginCode", SendLoginCodeRequestDto(email))
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:51:        execute("auth:verifyLoginCode", VerifyLoginCodeRequestDto(email, code))
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:57:        execute(
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:58:            "auth:sendRegistrationCode",
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:66:        execute(
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:67:            "auth:verifyRegistrationCode",
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:74:        execute("auth:refreshToken", RefreshTokenRequestDto(refreshToken))
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:79:        execute("auth:revokeToken", RevokeTokenRequestDto(refreshToken = refreshToken))
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:82:        execute("auth:revokeToken", RevokeTokenRequestDto(all = true))
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:84:    private suspend inline fun <reified Req : Any, reified Res> execute(
frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/KtorAuthRemoteDataSource.kt:92:                    appendPathSegments(verb)
```

Resource path fragments in either client (`users/`, `studies/`, `devices/`, `fitbits/`, `conversations/`, `apps/`, `admins/`):

```
$ grep -rnE "(users|studies|devices|fitbits|conversations|apps|admins)[/\"']" frontend/dashboard/src frontend/mobile --include='*.ts' --include='*.tsx' --include='*.kt' --exclude='*.test.*' --exclude-dir=test --exclude-dir=build --exclude-dir=androidHostTest
(no output; grep exit status 1)
```

Conclusion: both clients call only `auth:*` paths today, so route enforcement lands in one step and no permissive mode exists.

## D-11 substitution (developer-accepted deviation)

D-11 asks for one authorized resource call per role, made the way a client would. Neither client has resource-call code, and no screens are added in this phase. On 2026-11-04 the developer accepted these substitutes as a deviation from D-11:

1. the per-role pytest flow with OTP-issued tokens (`backend/api/tests/test_e2e_roles_flow.py`),
2. the mobile MockEngine bearer test (`ResourceCallBearerTest`), and
3. curl on the live API (`## Authorized resource call per role` below).

No new client code was written. Success criterion 5's "work in the dashboard" is proven as sign-in, session restore and sign-out, because the dashboard has no resource screens, under this accepted D-11 deviation.

## Prerequisites

| Needed | Who supplies it |
| ------ | --------------- |
| Couchbase and Sync Gateway (the API lifespan opens Couchbase; Postgres adapters arrive in Phases 4-5) | You: point `COUCHBASE_*` and `SYNC_GATEWAY_URL` at your own instance |
| Mongo (holds users and participants) | You: point `MONGO_URL` and `MONGO_DB` at your own instance |
| Docker daemon (OrbStack: `orb start`) | You |
| JDK and Android Studio with an emulator image | You: create an emulator in Device Manager |
| Xcode with an iOS simulator | You |
| Node 22 for the dashboard test suite (the dev server also runs on newer Node) | You |

Use a throwaway or development database. The seed writes an admin role wherever `MONGO_URL` points; never run it against a store holding real participant data.

What you can start locally:

```bash
# Redis (OTP codes and rate limits)
docker run --rm -p 6379:6379 redis:7-alpine

# Any SMTP sink on port 1025. Mailpit is one example (not verified by this plan);
# its web UI is on http://localhost:8025.
docker run --rm -p 1025:1025 -p 8025:8025 axllent/mailpit
```

SMTP is the only OTP channel and codes are never logged, so you read each code in the sink. The seed's `example.com` addresses only work with such a sink: a real SMTP server cannot deliver to them, which is deliberate.

## Stack

Put these values in `.env` at the repository root, on top of `.env.example`:

```
API_AUTH_JWT_SECRET=<32+ random characters>
API_AUTH_CODE_PEPPER=<32+ random characters>
REDIS_URL=redis://localhost:6379/0
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USE_TLS=false
SMTP_FROM_ADDRESS=openwellness@example.com
API_ENABLE_DOCS=true
```

Start, in order:

```bash
# 1. Seed (idempotent; prints the emails and the study and participant ids you need below)
cd backend/api && uv run --frozen python scripts/dev_seed.py

# 2. API on port 8000, which every client already defaults to
cd backend/api && uv run --frozen uvicorn openwellness_api.main:app --port 8000

# 3. Dashboard
cd frontend/dashboard && VITE_API_BASE_URL=http://127.0.0.1:8000/v1 npm run dev
```

Seed accounts: `dev-admin@example.com`, `dev-coach@example.com`, `dev-participant@example.com`; study `Dev Study`; participant number `DEV-1`. The Android emulator reaches the API at `http://10.0.2.2:8000/v1/` and the iOS simulator at `http://localhost:8000/v1/`; both are the existing defaults, so no client config changes.

Node 26 can run the dashboard dev server, but its test suite needs Node 22 (run it in a `node:22-bookworm-slim` container).

## Dashboard (coach and admin)

Open the Vite URL (http://localhost:5173).

1. Sign in as `dev-coach@example.com`: enter the email, request the code, read it in the sink, enter it. Expected: the signed-in dashboard shell appears.
2. Reload the page. Expected: you stay signed in (the session is restored by refreshing the token; no code is requested).
3. Sign out. Expected: you return to the sign-in screen, and reloading does not restore the session.
4. Repeat steps 1 to 3 as `dev-admin@example.com`.
5. Sign in as `dev-participant@example.com` with a fresh code. Expected: refused with "This account isn't authorized for the coaching dashboard." and no session is kept.

## Android emulator

Run the app from Android Studio on an emulator (no physical device, D-13).

1. Sign in as `dev-participant@example.com` with the code from the sink. Expected: you reach the signed-in screen.
2. Sign out. Expected: back to sign-in.
3. Try `dev-coach@example.com` with a fresh code. Expected: refused with the `auth_error_not_participant` text, "This app is for study participants. Staff can sign in on the coaching dashboard." and no session is saved.
4. Sign in again as the participant, force-stop and relaunch the app. Expected: the app shows sign-in again, because the mobile app has no session restore yet (assumption A-11-2). This is recorded behavior, not a failure.

## iOS simulator

Run the `iosApp` target from Xcode on a simulator (no physical device, D-13). Repeat the four Android steps with the same expected results.

## Authorized resource call per role

Neither client can make a resource call (see the D-11 substitution), so this uses curl against the live API with tokens from the real OTP flow. Take `STUDY` and `PID` from the seed output.

```bash
API=http://127.0.0.1:8000/v1
STUDY=<study id from the seed output>
PID=<participant id from the seed output>

# Sign in as <email>: send a code, read it in the sink, verify it, print the access token.
login() {
  curl -s -X POST "$API/auth:sendLoginCode" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\"}" > /dev/null
  read -r -p "Code for $1 (from the sink): " CODE
  curl -s -X POST "$API/auth:verifyLoginCode" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"code\":\"$CODE\"}" | jq -r .accessToken
}
```

| Caller | Request | Expected |
| ------ | ------- | -------- |
| admin | `curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $ADMIN" $API/users` | 200 |
| coach | `curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $COACH" $API/studies/$STUDY/participants` | 200, listing the seeded participant |
| coach | `curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $COACH" $API/users/$PID/weights` | 200 |
| participant | `curl -s -X POST -H "Authorization: Bearer $PART" -H 'Content-Type: application/json' -d '{"weight":70.5}' $API/users/$PID/weights` | 201, `updatedBy` is the participant's user id |
| participant | `curl -s -H "Authorization: Bearer $PART" $API/users/$PID/weights` | 200, the new weight is listed |
| anonymous | `curl -s -o /dev/null -w '%{http_code}\n' $API/users/$PID/weights` | 401 |
| participant, another id | `curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $PART" $API/users/someone-else/weights` | 404 |

Set the tokens with `ADMIN=$(login dev-admin@example.com)`, and likewise `COACH` and `PART`.

Owner-scoped calls use `weights` and not another owner-scoped list on purpose (assumption A-12-1): 13 routers' list calls use `get_for_owner_between`, which their Couchbase adapters do not implement, so they answer 500 on live stores. That predates this phase and fakes hide it, so this document does not use them.

## Sign-off

Date: ____________  Signed by: ____________

| Target | Role | Expected | Pass | Notes |
| ------ | ---- | -------- | ---- | ----- |
| Dashboard | coach | sign in, reload restores, sign out | | |
| Dashboard | admin | sign in, reload restores, sign out | | |
| Dashboard | participant | refused with the staff-only message | | |
| Android emulator | participant | sign in, sign out, relaunch shows sign-in | | |
| Android emulator | coach | refused with `auth_error_not_participant` text | | |
| iOS simulator | participant | sign in, sign out, relaunch shows sign-in | | |
| iOS simulator | coach | refused with `auth_error_not_participant` text | | |
| curl | admin | `GET /users` 200 | | |
| curl | coach | participants list 200, weights 200 | | |
| curl | participant | `POST` 201, `GET` 200 | | |
| curl | anonymous | 401 | | |
| curl | participant, another id | 404 | | |
