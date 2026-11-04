"""The authorization policy as data, one row per resource module.

Mirrors ADR 0007 (Policy table) and the owner binding of ADR 0005. It is checked
against both by ``tests/test_adr_policy_table.py`` and never built from them at
runtime: the API does not read the ADR files.
"""

from __future__ import annotations

from dataclasses import dataclass

OPS = ("get", "list", "create", "patch", "delete", "undelete", "purge")

# Custom methods that reuse a table op (assumption A4, developer-confirmed).
CUSTOM_OPS = {"conversation": {"search": "list"}, "study": {"lookup": "get"}}


@dataclass(frozen=True)
class Row:
    """One ADR 0007 row. Admin is global; purge is held by admin alone."""

    route: str
    self_scope: str | None
    coach_scope: str | None
    self_ops: frozenset[str]
    coach_ops: frozenset[str]
    admin_ops: frozenset[str]
    # What ADR 0005 says `owner` holds: "participant", "study" or "membership".
    binding: str | None


_NONE: frozenset[str] = frozenset()
_GET = frozenset({"get"})
_READ = frozenset({"get", "list"})
_READ_PATCH = frozenset({"get", "list", "patch"})
_SIX = frozenset(OPS) - {"purge"}  # every op except the hard delete
_ALL = frozenset(OPS)

POLICY: dict[str, Row] = {
    "actigraph_record": Row(
        "/v1/users/{user}/actigraphRecords", "self-owner", "coach-study", _READ, _READ,
        _ALL, "participant",
    ),
    "admin": Row("/v1/admins", None, None, _NONE, _NONE, _ALL, None),
    "app": Row("/v1/apps", None, None, _NONE, _NONE, _ALL, None),
    "asset": Row(
        "/v1/users/{user}/assets", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "card": Row(
        "/v1/users/{user}/cards", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "condition": Row(
        "/v1/users/{user}/conditions", "self-owner", "coach-study", _READ, _SIX, _ALL,
        "participant",
    ),
    "conversation": Row(
        "/v1/conversations", "self-member-conversation", "coach-study", _READ, _SIX,
        _ALL, "membership",
    ),
    "daily_state": Row(
        "/v1/users/{user}/dailyStates", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "device": Row("/v1/devices", "self-device", None, _READ, _NONE, _ALL, None),
    "fitbit": Row("/v1/fitbits", "self-fitbit", None, _GET, _NONE, _ALL, None),
    "fitbit_heart_record": Row(
        "/v1/users/{user}/fitbitHeartRecords", "self-owner", "coach-study", _READ,
        _READ, _ALL, "participant",
    ),
    "fitbit_record": Row(
        "/v1/users/{user}/fitbitRecords", "self-owner", "coach-study", _READ, _READ,
        _ALL, "participant",
    ),
    "fitbit_sleep": Row(
        "/v1/users/{user}/fitbitSleeps", "self-owner", "coach-study", _READ, _READ,
        _ALL, "participant",
    ),
    "fitbit_sleep_session": Row(
        "/v1/users/{user}/fitbitSleepSessions", "self-owner", "coach-study", _READ,
        _READ, _ALL, "participant",
    ),
    "fitbit_weight": Row(
        "/v1/users/{user}/fitbitWeights", "self-owner", "coach-study", _READ, _READ,
        _ALL, "participant",
    ),
    "goal": Row(
        "/v1/users/{user}/goals", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "job_rule": Row(
        "/v1/users/{user}/jobRules", "self-owner", "coach-study", _READ, _SIX, _ALL,
        "participant",
    ),
    "message": Row(
        "/v1/users/{user}/messages", "self-owner", "coach-study", _READ, _SIX, _ALL,
        "participant",
    ),
    "message_draft": Row(
        "/v1/users/{user}/messageDrafts", "self-owner", "coach-study", _READ, _SIX,
        _ALL, "participant",
    ),
    "meta_data": Row(
        "/v1/users/{user}/metaData", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "participant": Row(
        "/v1/studies/{study}/participants", "self-participant", "coach-study", _GET,
        _READ_PATCH, _ALL, None,
    ),
    "participant_group": Row(
        "/v1/users/{user}/participantGroups", "self-member-group", "coach-study", _READ,
        _SIX, _ALL, "membership",
    ),
    "physical_activity": Row(
        "/v1/users/{user}/physicalActivities", "self-owner", "coach-study", _SIX, _READ,
        _ALL, "participant",
    ),
    "post": Row(
        "/v1/users/{user}/posts", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "session": Row(
        "/v1/users/{user}/sessions", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "shared_goal_progress": Row(
        "/v1/users/{user}/sharedGoalProgress", "self-owner", "coach-study", _READ,
        _READ, _ALL, "participant",
    ),
    "study": Row("/v1/studies", "self-study", "coach-study", _GET, _READ, _ALL, None),
    "study_message": Row(
        "/v1/studies/{study}/studyMessages", "self-study", "coach-study", _READ, _SIX,
        _ALL, None,
    ),
    "study_settings": Row(
        "/v1/studies/{study}/studySettings", "self-study", "coach-study", _READ, _SIX,
        _ALL, "study",
    ),
    "survey_result": Row(
        "/v1/users/{user}/surveyResults", "self-owner", "coach-study", _SIX, _READ,
        _ALL, "participant",
    ),
    "user": Row("/v1/users", "self-user", None, _GET, _NONE, _ALL, None),
    "user_food": Row(
        "/v1/users/{user}/userFoods", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "user_settings": Row(
        "/v1/users/{user}/userSettings", "self-owner", "coach-study", _READ, _SIX, _ALL,
        "participant",
    ),
    "user_sleep": Row(
        "/v1/users/{user}/userSleeps", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "user_stress": Row(
        "/v1/users/{user}/userStresses", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
    "weight": Row(
        "/v1/users/{user}/weights", "self-owner", "coach-study", _SIX, _READ, _ALL,
        "participant",
    ),
}
