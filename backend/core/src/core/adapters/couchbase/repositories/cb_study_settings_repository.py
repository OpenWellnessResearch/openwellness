"""Couchbase repository for StudySettings."""

from typing import Generic, Type

from ....application.repositories.study_settings_repository import (
    SomeStudySettings,
    StudySettingsRepository,
)
from ....domain.models.study_settings import StudySettings
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_study_settings import CBStudySettings
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBStudySettingsRepository(
    StudySettingsRepository,
    CBBaseRepository[SomeStudySettings, CBStudySettings],
    Generic[SomeStudySettings],
):
    """Couchbase repository for the StudySettings entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeStudySettings] = StudySettings,
        persistence_type: type[CBStudySettings] = CBStudySettings,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_study_id(self, study_id: str) -> SomeStudySettings | None:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND studyId = $studyId "
            f"ORDER BY createdAt"
        )
        params = {"type": CBStudySettings.type, "studyId": study_id}
        results = self.repo.get_by_query(q, params)
        result = None if len(results) == 0 else results[-1]
        return self.init_entity_valid_fields(result) if result else None
