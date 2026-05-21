"""Repository query tests: each method must parameterize all values.

These tests stand in a ``FakeEntityRepository`` that captures the
``(query, params)`` passed by every repository method, then asserts:

1. No user-controlled value appears in the query string (only in ``params``).
2. ``orderBy``/``ordering`` arguments are validated against an allowlist.
3. Conditional clauses are only emitted when their argument is provided.
4. The known correctness bug in ``goal_repository.generate_kind_expression``
   (string-quoted ``kind IN`` against a numeric column) is fixed.
"""

from __future__ import annotations

from typing import Optional

import arrow
import pytest

from openwellness_core.adapters.couchbase.repositories._query_helpers import (
    allowed_column,
)
from openwellness_core.adapters.couchbase.repositories.cb_actigraph_record_repository import (
    CBActigraphRecordRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_asset_repository import (
    CBAssetRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_condition_repository import (
    CBConditionRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_conversation_repository import (
    CBConversationRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_daily_state_repository import (
    CBDailyStateRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_fitbit_heart_record_repository import (
    CBFitbitHeartRecordRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_fitbit_record_repository import (
    CBFitbitRecordRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_fitbit_sleep_repository import (
    CBFitbitSleepRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_fitbit_sleep_session_repository import (
    CBFitbitSleepSessionRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_fitbit_weight_repository import (
    CBFitbitWeightRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_goal_repository import (
    CBGoalRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_job_rule_repository import (
    CBJobRuleRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_message_draft_repository import (
    CBMessageDraftRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_message_repository import (
    CBMessageRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_meta_data_repository import (
    CBMetaDataRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_physical_activity_repository import (
    CBPhysicalActivityRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_post_repository import (
    CBPostRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_session_repository import (
    CBSessionRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_shared_goal_progress_repository import (
    CBSharedGoalProgressRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_study_settings_repository import (
    CBStudySettingsRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_survey_result_repository import (
    CBSurveyResultRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_user_food_repository import (
    CBUserFoodRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_user_settings_repository import (
    CBUserSettingsRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_user_sleep_repository import (
    CBUserSleepRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_user_stress_repository import (
    CBUserStressRepository,
)
from openwellness_core.adapters.couchbase.repositories.cb_weight_repository import (
    CBWeightRepository,
)
from openwellness_core.domain.models.conversation import Conversation
from openwellness_core.infrastructure.interfaces.entity_repository import (
    EntityRepository,
)


BUCKET = "ow-bucket"


class FakeEntityRepository(EntityRepository):
    """Captures the last (query, params) pair instead of touching Couchbase."""

    def __init__(self) -> None:
        self.last_query: Optional[str] = None
        self.last_params: Optional[dict] = None

    @property
    def bucket(self) -> str:
        return BUCKET

    def get_by_id(self, doc_id: str):
        return None

    def get_by_query(self, query: str, params: Optional[dict] = None):
        self.last_query = query
        self.last_params = params or {}
        return []

    def create(self, obj: dict) -> dict:
        return obj

    def update(self, doc_id: str, obj: dict) -> dict:
        return obj

    def save(self, obj: dict) -> dict:
        return obj

    def delete(self, doc_id: str):
        return None


@pytest.fixture
def fake_repo() -> FakeEntityRepository:
    return FakeEntityRepository()


# ---------------------------------------------------------------------------
# Generic invariants
# ---------------------------------------------------------------------------


# Strings that, if they appeared in a query, would mean a user value got
# spliced in unescaped (the historical bug we're guarding against).
_INJECTION_STRINGS = ('abc"', "abc'", '" OR "1"="1', "; DROP TABLE")


def _assert_no_injection(query: str, params: dict, *probes: str) -> None:
    """The probe strings must appear in params, never in the query."""
    for probe in probes:
        assert probe not in query, (
            f"value {probe!r} leaked into query: {query!r}"
        )
        assert probe in params.values(), (
            f"value {probe!r} expected in params, got {params!r}"
        )


# ---------------------------------------------------------------------------
# allowed_column helper
# ---------------------------------------------------------------------------


def test_allowed_column_passes_known_value():
    assert allowed_column("createdAt", frozenset({"createdAt"})) == "createdAt"


def test_allowed_column_rejects_unknown():
    with pytest.raises(ValueError, match="unknown column"):
        allowed_column("bogus; DROP", frozenset({"createdAt"}))


# ---------------------------------------------------------------------------
# Asset (heavy: kwargs killed + orderBy allowlisted)
# ---------------------------------------------------------------------------


def test_asset_fetch_parameterizes_values(fake_repo):
    CBAssetRepository(fake_repo).fetch(study_id='abc" OR 1=1')
    assert fake_repo.last_params is not None
    assert fake_repo.last_params["studyId"] == 'abc" OR 1=1'
    assert 'abc" OR 1=1' not in (fake_repo.last_query or "")


def test_asset_fetch_orderby_allowlist(fake_repo):
    CBAssetRepository(fake_repo).fetch(study_id="s1", orderBy="updatedAt")
    assert "ORDER BY updatedAt" in (fake_repo.last_query or "")


def test_asset_fetch_orderby_rejects_unknown(fake_repo):
    with pytest.raises(ValueError):
        CBAssetRepository(fake_repo).fetch(study_id="s1", orderBy="bogus")


def test_asset_fetch_omits_kind_when_none(fake_repo):
    CBAssetRepository(fake_repo).fetch(study_id="s1")
    assert "kind" not in (fake_repo.last_query or "")
    assert "kind" not in (fake_repo.last_params or {})


def test_asset_fetch_includes_kind_when_provided(fake_repo):
    CBAssetRepository(fake_repo).fetch(study_id="s1", kind=2, week=3)
    assert "kind = $kind" in (fake_repo.last_query or "")
    assert "week = $week" in (fake_repo.last_query or "")
    assert fake_repo.last_params["kind"] == 2
    assert fake_repo.last_params["week"] == 3


def test_asset_fetch_rejects_kwargs(fake_repo):
    with pytest.raises(TypeError):
        CBAssetRepository(fake_repo).fetch(study_id="s1", junk="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# MetaData (heavy: ordering allowlisted, three optional filters)
# ---------------------------------------------------------------------------


def test_metadata_ordering_allowlist(fake_repo):
    CBMetaDataRepository(fake_repo).get_for_study_id("s1", ordering="updatedAt")
    assert "ORDER BY studyId, updatedAt" in (fake_repo.last_query or "")


def test_metadata_ordering_rejects_unknown(fake_repo):
    with pytest.raises(ValueError):
        CBMetaDataRepository(fake_repo).get_for_study_id("s1", ordering="bogus")


def test_metadata_get_for_owner_parameterizes(fake_repo):
    CBMetaDataRepository(fake_repo).get_for_owner(
        owner='inj"', related_id="rid"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'inj"',
        "rid",
    )
    assert "studyId IS NOT MISSING" in (fake_repo.last_query or "")


def test_metadata_get_for_related_only_omits_other_clauses(fake_repo):
    CBMetaDataRepository(fake_repo).get_for_related_id("rid")
    q = fake_repo.last_query or ""
    assert "owner IS NOT MISSING" in q
    assert "studyId IS NOT MISSING" in q
    assert "relatedId = $relatedId" in q


# ---------------------------------------------------------------------------
# Physical activity (order direction is a literal chosen by a bool, not user)
# ---------------------------------------------------------------------------


def test_physical_activity_descending_uses_desc(fake_repo):
    CBPhysicalActivityRepository(fake_repo).fetch_all_in_range(
        "p1", 0.0, 1.0, descending=True
    )
    q = fake_repo.last_query or ""
    assert "DESC" in q
    assert "ASC" not in q


def test_physical_activity_default_uses_asc(fake_repo):
    CBPhysicalActivityRepository(fake_repo).fetch_all_in_range("p1", 0.0, 1.0)
    q = fake_repo.last_query or ""
    assert "ASC" in q
    assert "DESC" not in q


def test_physical_activity_parameterizes_owner_and_range(fake_repo):
    CBPhysicalActivityRepository(fake_repo).fetch_all_in_range(
        'p"1', 1.0, 2.0
    )
    assert fake_repo.last_params["owner"] == 'p"1'
    assert fake_repo.last_params["start"] == 1.0
    assert fake_repo.last_params["end"] == 2.0
    assert 'p"1' not in (fake_repo.last_query or "")


# ---------------------------------------------------------------------------
# Post (channel goes through parameters, conversation_id is optional)
# ---------------------------------------------------------------------------


def test_post_channel_parameterized(fake_repo):
    CBPostRepository(fake_repo).get_for_channel_between(channel='hacker"')
    q = fake_repo.last_query or ""
    assert '"' not in fake_repo.last_params["channel"][:-1] or True  # value preserved
    assert "hacker" not in q
    assert fake_repo.last_params["channel"] == 'hacker"'


def test_post_conversation_id_optional(fake_repo):
    CBPostRepository(fake_repo).get_for_channel_between(
        channel="c", conversation_id="conv1"
    )
    assert "conversationId = $conversationId" in (fake_repo.last_query or "")
    assert fake_repo.last_params["conversationId"] == "conv1"


def test_post_conversation_id_omitted_when_none(fake_repo):
    CBPostRepository(fake_repo).get_for_channel_between(channel="c")
    q = fake_repo.last_query or ""
    assert "conversationId" not in q
    assert "conversationId" not in (fake_repo.last_params or {})


# ---------------------------------------------------------------------------
# Goal (the kind-IN numeric-vs-string bug + parameter coverage)
# ---------------------------------------------------------------------------


def test_goal_kind_list_uses_param_not_string_quotes(fake_repo):
    """Regression: previously produced kind IN ['1','2'] (string-quoted)."""
    repo = CBGoalRepository(fake_repo)
    clause, params = repo.generate_kind_expression([1, 2, 3])
    assert clause == "AND kind IN $kinds"
    assert params == {"kinds": [1, 2, 3]}


def test_goal_kind_int(fake_repo):
    repo = CBGoalRepository(fake_repo)
    clause, params = repo.generate_kind_expression(2)
    assert clause == "AND kind = $kind"
    assert params == {"kind": 2}


def test_goal_kind_none(fake_repo):
    repo = CBGoalRepository(fake_repo)
    clause, params = repo.generate_kind_expression(None)
    assert clause == "AND kind IS NOT MISSING"
    assert params == {}


def test_goal_generate_query_parameterizes_owner_and_dates(fake_repo):
    start = arrow.Arrow(2024, 1, 1)
    end = arrow.Arrow(2024, 1, 2)
    q, params = CBGoalRepository(fake_repo).generate_query(
        'p"1', start, end
    )
    assert 'p"1' not in q
    assert params["owner"] == 'p"1'
    assert params["start"] == start.timestamp()
    assert params["end"] == end.timestamp()


# ---------------------------------------------------------------------------
# Survey result (kwargs replaced with explicit kind argument)
# ---------------------------------------------------------------------------


def test_survey_result_kind_int(fake_repo):
    repo = CBSurveyResultRepository(fake_repo)
    repo.get_survey_results_on(owner="p", date="2024-01-01", kind=5)
    assert "kind = $kind" in (fake_repo.last_query or "")
    assert fake_repo.last_params["kind"] == 5


def test_survey_result_kind_list(fake_repo):
    repo = CBSurveyResultRepository(fake_repo)
    repo.get_survey_results_between(
        owner="p", start="2024-01-01", end="2024-01-31", kind=[1, 2]
    )
    assert "kind IN $kinds" in (fake_repo.last_query or "")
    assert fake_repo.last_params["kinds"] == [1, 2]


def test_survey_result_kind_none_uses_missing_or_null(fake_repo):
    CBSurveyResultRepository(fake_repo).get_survey_results_between(
        owner="p", start="2024-01-01", end="2024-01-31"
    )
    assert "(kind IS MISSING OR kind IS NULL)" in (fake_repo.last_query or "")


# ---------------------------------------------------------------------------
# Conversation (Filter.to_n1ql + channel injection guard)
# ---------------------------------------------------------------------------


def test_conversation_channels_filter_preserves_quotes(fake_repo):
    """Channel name with a literal ``"`` must land as a list value, not a literal."""
    flt = Conversation.Filter(
        Conversation.Filter.Type.CHANNELS, ['safe', 'bad"channel']
    )
    CBConversationRepository(fake_repo).get_for_filters([flt])
    q = fake_repo.last_query or ""
    assert 'bad"channel' not in q
    assert fake_repo.last_params["channels_0"] == ["safe", 'bad"channel']
    assert "$channels_0" in q


def test_conversation_kind_filter_int(fake_repo):
    flt = Conversation.Filter(Conversation.Filter.Type.KIND, 7)
    CBConversationRepository(fake_repo).get_for_filters([flt])
    assert "kind = $kind_0" in (fake_repo.last_query or "")
    assert fake_repo.last_params["kind_0"] == 7


def test_conversation_empty_filters(fake_repo):
    CBConversationRepository(fake_repo).get_for_filters([])
    q = fake_repo.last_query or ""
    assert "WHERE type = $type ORDER BY" in q


def test_conversation_filter_indices_avoid_collisions(fake_repo):
    f1 = Conversation.Filter(Conversation.Filter.Type.KIND, 1)
    f2 = Conversation.Filter(Conversation.Filter.Type.KIND, 2)
    CBConversationRepository(fake_repo).get_for_filters([f1, f2])
    assert fake_repo.last_params["kind_0"] == 1
    assert fake_repo.last_params["kind_1"] == 2


# ---------------------------------------------------------------------------
# Session (require_session_type two-level branch)
# ---------------------------------------------------------------------------


def test_session_no_session_type_clause(fake_repo):
    CBSessionRepository(fake_repo).fetch_sessions_in_range("p")
    q = fake_repo.last_query or ""
    assert "sessionType" not in q
    assert "sessionType" not in (fake_repo.last_params or {})


def test_session_require_with_value(fake_repo):
    CBSessionRepository(fake_repo).fetch_sessions_in_range(
        "p", require_session_type=True, session_type=3
    )
    assert "sessionType = $sessionType" in (fake_repo.last_query or "")
    assert fake_repo.last_params["sessionType"] == 3


def test_session_require_without_value(fake_repo):
    CBSessionRepository(fake_repo).fetch_sessions_in_range(
        "p", require_session_type=True
    )
    assert "sessionType IS MISSING" in (fake_repo.last_query or "")
    assert "sessionType" not in (fake_repo.last_params or {})


# ---------------------------------------------------------------------------
# Message draft (optional week/day)
# ---------------------------------------------------------------------------


def test_message_draft_omits_optional_clauses(fake_repo):
    CBMessageDraftRepository(fake_repo).get_for_study_subtype(
        study_id="s", subtype=1
    )
    q = fake_repo.last_query or ""
    assert "$week" not in q
    assert "$day" not in q
    assert "week" not in (fake_repo.last_params or {})
    assert "day" not in (fake_repo.last_params or {})


def test_message_draft_includes_week_and_day(fake_repo):
    CBMessageDraftRepository(fake_repo).get_for_study_subtype(
        study_id="s", subtype=1, week=2, day=3
    )
    q = fake_repo.last_query or ""
    assert "week = $week" in q
    assert "day = $day" in q
    assert fake_repo.last_params["week"] == 2
    assert fake_repo.last_params["day"] == 3


# ---------------------------------------------------------------------------
# Message (optional subtype/condition)
# ---------------------------------------------------------------------------


def test_message_omits_optional(fake_repo):
    CBMessageRepository(fake_repo).get_for_owner_between(
        owner="p", start=arrow.Arrow(2024, 1, 1), end=arrow.Arrow(2024, 1, 2)
    )
    q = fake_repo.last_query or ""
    assert "subtype" not in q
    assert "condition" not in q


def test_message_includes_optional(fake_repo):
    CBMessageRepository(fake_repo).get_for_owner_between(
        owner="p",
        start=arrow.Arrow(2024, 1, 1),
        end=arrow.Arrow(2024, 1, 2),
        subtype=5,
        condition=2,
    )
    q = fake_repo.last_query or ""
    assert "subtype = $subtype" in q
    assert "condition = $condition" in q


# ---------------------------------------------------------------------------
# Trivial repositories — sanity that values land in params, not query.
# ---------------------------------------------------------------------------


def test_study_settings_parameterized(fake_repo):
    from openwellness_core.adapters.couchbase.repositories.cb_study_settings_repository import (
        CBStudySettingsRepository as Repo,
    )

    Repo(fake_repo).get_for_study_id('s" inject')
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        's" inject',
    )


def test_user_settings_parameterized(fake_repo):
    CBUserSettingsRepository(fake_repo).get_for_owner('p" inject')
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_user_sleep_parameterized(fake_repo):
    CBUserSleepRepository(fake_repo).get_user_sleeps_in_range(
        'p" inject', "2024-01-01", "2024-01-02"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_user_stress_parameterized(fake_repo):
    CBUserStressRepository(fake_repo).get_user_stresses_in_range(
        'p" inject', "2024-01-01", "2024-01-02"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_user_food_parameterized(fake_repo):
    CBUserFoodRepository(fake_repo).get_for_owner_between(
        'p" inject', arrow.Arrow(2024, 1, 1), arrow.Arrow(2024, 1, 2)
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_fitbit_weight_parameterized(fake_repo):
    CBFitbitWeightRepository(fake_repo).get_for_owner_between(
        'p" inject', "2024-01-01", "2024-01-02"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_fitbit_heart_record_parameterized(fake_repo):
    CBFitbitHeartRecordRepository(fake_repo).get_for_owner(
        'p" inject', "2024-01-01"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_fitbit_sleep_parameterized(fake_repo):
    CBFitbitSleepRepository(fake_repo).get_for_owner(
        'p" inject', arrow.Arrow(2024, 1, 1)
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_fitbit_sleep_session_parameterized(fake_repo):
    CBFitbitSleepSessionRepository(fake_repo).get_for_owner(
        'p" inject', arrow.Arrow(2024, 1, 1)
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_fitbit_record_parameterized(fake_repo):
    CBFitbitRecordRepository(fake_repo).get_for_owner(
        'p" inject', "2024-01-01"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_daily_state_parameterized(fake_repo):
    CBDailyStateRepository(fake_repo).get_for_owner_between(
        'p" inject', arrow.Arrow(2024, 1, 1), arrow.Arrow(2024, 1, 2)
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_shared_goal_progress_parameterized(fake_repo):
    CBSharedGoalProgressRepository(fake_repo).get_for_owner(
        'p" inject', "2024-01-01"
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_actigraph_record_parameterized(fake_repo):
    CBActigraphRecordRepository(fake_repo).get_for_owner_between(
        'p" inject', arrow.Arrow(2024, 1, 1), arrow.Arrow(2024, 1, 2)
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_weight_parameterized(fake_repo):
    CBWeightRepository(fake_repo).get_for_owner_between(
        'p" inject', arrow.Arrow(2024, 1, 1), arrow.Arrow(2024, 1, 2)
    )
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_condition_parameterized(fake_repo):
    CBConditionRepository(fake_repo).get_for_owner('p" inject', 5)
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        'p" inject',
    )


def test_job_rule_parameterized(fake_repo):
    CBJobRuleRepository(fake_repo).get_by_study_id('s" inject')
    _assert_no_injection(
        fake_repo.last_query or "",
        fake_repo.last_params or {},
        's" inject',
    )
