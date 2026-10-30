# 0006. Coach study scope and claim

- Status: Accepted
- Date: 2026-10-30
- Decisions: D-02, D-03, D-04

## Context

The research default for v1 was a bare `coach` role gate: any coach could read any participant. The developer chose study scope instead (D-02), because a coach who can reach every study's participant health data is the over-reach Pitfall 2 warns about, and retrofitting scope after data and sync policy exist is expensive. This ADR fixes where a coach's studies are stored, how they reach the API and sync layers, and how stale they can get. ADR 0007 turns it into per-resource cells and the write checks.

## Decision

- A coach acts only within the studies listed at `roles.coach.studies` (a list of study ids) in the `roles` dict of their `User` record. No `StudyStaff` or membership entity exists in v1 (deferred).
- Only admins edit that list. A coach cannot edit it, and a patch to `roles` is never accepted from a non-admin (ADR 0007 mass-assignment caveat).
- The access token carries the list as the `coach_studies` claim (a list of strings). The name is distinct from `roles`, so `roles` stays a flat list of role keys (ADR 0004). A user without the coach role carries no `coach_studies` or an empty list, which matches no study.
- Admins are global (D-04). They see and manage every study and need no study list.
- The legacy `Admin.study_ids` field is not the source of truth and is not read for authorization.
- Staleness: claims are re-minted from the user record at every refresh (`AuthService.refresh_token` re-reads the user and rebuilds the claims), so a study removed from `roles.coach.studies` stays reachable for at most `API_AUTH_ACCESS_TTL_SECONDS` (900 s default) plus `jwt_leeway_seconds` (30 s), 930 s in total. An admin who needs immediate effect revokes the coach's sessions, which stops further refreshes.
- A participant has no study claim (ADR 0004). Their study is derived from the Participant record on each request (ADR 0007 `self-study`).

## Consequences

- Every coach-reachable query filters by `study_id` in `coach_studies`, and every coach write also checks the target owner's Participant study (ADR 0007 `coach-study`).
- Phase 2 reads the claim in its coach dependency and mints it at login and refresh. Phase 6 sync policy uses the same claim, so a coach stream and an API route agree on the same studies.
- Adding a coach to a study takes effect at the next refresh at the latest, and a removal takes up to the staleness window above unless sessions are revoked.
- Costly to reverse: the claim name, the storage path and the scope check are encoded in route guards, tests and sync rules. A membership entity can replace the storage path later without changing the claim.
