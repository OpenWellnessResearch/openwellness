"""Mongo repository for Study."""

from ....application.repositories.study_repository import StudyRepository
from ....domain.models.study import Study
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_study import MongoStudy
from .mongo_base_repository import MongoBaseRepository


class MongoStudyRepository(StudyRepository, MongoBaseRepository[Study, MongoStudy]):
    """Mongo repository for the Study entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        persistence_type: type[MongoStudy] = MongoStudy,
    ) -> None:
        super().__init__(mongo_repo, Study, persistence_type)
        self.entity_type = Study

    def get_by_name(self, name: str) -> Study | None:
        q = {"name": {"$regex": f"^{name}$", "$options": "i"}}
        results = self.get_by_query(q)
        if len(results) == 0:
            return None
        if len(results) > 1:
            raise ValueError(f"Multiple studies found with name {name} - {results}")
        return results[0]
