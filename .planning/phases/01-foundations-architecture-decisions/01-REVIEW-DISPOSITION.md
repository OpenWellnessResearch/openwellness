# Phase 01 review disposition

Source: 01-REVIEW.md (0 critical, 4 warning, 5 info). Every finding starts `open`; triage with `/gsd-code-review 01 --fix` or by editing this table.

| ID | Severity | File | Summary | Disposition |
| --- | --- | --- | --- | --- |
| WR-01 | warning | backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py:56-62 | Malformed userId/assignedCoachId in a body returns 404 (not 400) and echoes the raw value | open |
| WR-02 | warning | backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py:71-77 | Stored-document hydration ValidationError surfaces as client 400 leaking stored fields | open |
| WR-03 | warning | backend/api/src/openwellness_api/main.py:50-58 | container.wire before the try leaks the Couchbase cluster on failure | open |
| WR-04 | warning | backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_refresh_session_repository.py:44-56 | ensure_indexes maps every OperationFailure to "drop the index" advice | open |
| IN-01 | info | backend/core/src/openwellness_core/infrastructure/config/settings.py | Missing/mistyped OPENWELLNESS_ENV_FILE silently ignored | open |
| IN-02 | info | .env.example | Omits API_AUTH_JWT_SECRET, API_AUTH_CODE_PEPPER, SMTP_* required at boot | open |
| IN-03 | info | (several) | Style drift: long line, mid-file imports, missing __future__ annotations | open |
| IN-04 | info | mongo_participant_repository.py | Legacy doc without studyId yields study_id=None despite str type | open |
| IN-05 | info | backend/api/src/openwellness_api/main.py | Catch-all 500 sits outside CORSMiddleware (pre-existing) | open |
