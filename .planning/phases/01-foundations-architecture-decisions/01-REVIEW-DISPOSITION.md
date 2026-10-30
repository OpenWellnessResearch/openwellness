---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`MongoParticipantRepository._to_doc` makes legacy participants un-patchable and un-archivable, with a misleading 404"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "New catch-all 500 handler returns no CORS headers, and every unhandled error is logged twice"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "ADR 0007 omits two live routes, and one of them can bypass the membership scope the ADR defines"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "`APP_*` variables listed in `.env.example` are read with `os.environ`, so they are silently ignored on direct runs"
  - id: WR-05
    severity: warning
    disposition: skipped
    title: "Unauthenticated `POST /v1/users` now answers 409 ALREADY_EXISTS, an email-existence oracle"
  - id: IN-01
    severity: info
    disposition: open
    title: "`.env.example` omits settings the API refuses to boot without"
  - id: IN-02
    severity: info
    disposition: open
    title: "CI concurrency group cancels in-progress runs on `main`"
  - id: IN-03
    severity: info
    disposition: open
    title: "Dependency Rule is asserted in docs but not enforced by any test or CI step"
  - id: IN-04
    severity: info
    disposition: open
    title: "Unused parameter and a duplicated default collection name"
  - id: IN-05
    severity: info
    disposition: open
    title: "Style drift from project conventions in new files"
  - id: IN-06
    severity: info
    disposition: open
    title: "`resolve_env_file` locates the repo root by the `docker-compose.yml` marker and `env_file` is bound at import"
open: 6
total: 11
recorded: 2026-10-30T17:24:16.046Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 01-REVIEW-FIX.md |
| WR-02 | warning | fixed | 01-REVIEW-FIX.md |
| WR-03 | warning | fixed | 01-REVIEW-FIX.md |
| WR-04 | warning | fixed | 01-REVIEW-FIX.md |
| WR-05 | warning | skipped | 01-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
