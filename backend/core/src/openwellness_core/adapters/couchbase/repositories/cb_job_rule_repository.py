"""Couchbase repository for JobRule."""

from typing import Generic, Type

from ....application.repositories.job_rule_repository import (
    JobRuleRepository,
    SomeJobRule,
)
from ....domain.models.job_rule import JobRule
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_job_rule import CBJobRule
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBJobRuleRepository(
    CBBaseRepository[SomeJobRule, CBJobRule],
    JobRuleRepository,
    Generic[SomeJobRule],
):
    """Couchbase repository for the JobRule entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeJobRule] = JobRule,
        persistence_type: type[CBJobRule] = CBJobRule,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type: Type[SomeJobRule] = entity_type

    def get_by_study_id(self, study_id: str) -> list[SomeJobRule]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} USE KEYS ( "
            f"SELECT RAW meta().id "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND studyId = $studyId "
            f"ORDER BY createdAt"
            f")"
        )
        params = {"type": CBJobRule.type, "studyId": study_id}
        return [
            self.init_entity_valid_fields(item)
            for item in self.repo.get_by_query(q, params)
        ]

    def get_by_study_subtype(self, study_id: str, subtype: int) -> SomeJobRule | None:
        fetched = self.repo.get_by_id(f"JobRule:{study_id}:{subtype}")
        if not fetched:
            return None
        return self.init_entity_valid_fields(fetched)
