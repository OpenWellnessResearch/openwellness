# 0004. Access token format

- Status: Accepted (implementation in Phase 3)
- Date: 2026-10-30
- Decisions: D-13

## Context

Access tokens are HS256 JWTs signed with a single shared secret (`API_AUTH_JWT_SECRET`). That secret cannot be handed to PowerSync, the dashboard or the mobile app, so none of them can verify a token without being able to forge one. PowerSync must verify tokens without the API secret.

## Decision

- Access tokens are JWTs signed with EdDSA (Ed25519) and carry a `kid` header.
- Public keys are published as a JWKS at `/.well-known/jwks.json`. Several keys may be listed during rotation, and `kid` selects one.
- Claim set: `iss`, `sub` (user id), `aud`, `iat`, `exp`, `jti`, `typ="access"`, `participant` (bare participant id), `roles` (the list of role keys), plus the coach study claim defined in ADR 0006.
- There is no study claim for participants. The server derives a participant's study from the Participant record named by the `participant` claim on each request (ADR 0007 scope predicates), so a study move needs no token refresh and policy never depends on a claim that does not exist.
- Access TTL defaults to 900 s (`API_AUTH_ACCESS_TTL_SECONDS`) with 30 s leeway.
- Refresh tokens stay opaque random strings, stored only as sha256 hashes and rotated single-use.
- PowerSync gets a separate short-lived token minted by an authenticated API endpoint, with `aud=powersync`, signed by the same key set. The API signing key never leaves the API.
- HS256 is retired.

## Consequences

- The dashboard, mobile and PowerSync all verify through the JWKS.
- Key rotation needs a documented procedure (Phase 12).
- Costly to reverse, since three verifiers depend on it.
- Phase 3 implements this; until then the running API still issues HS256 tokens.
