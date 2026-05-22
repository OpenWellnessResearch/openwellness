"""Couchbase repository for Cards."""

from ....application.repositories.card_repository import CardRepository, SomeCard
from ....domain.models.card import Card
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_card import CBCard
from .cb_base_repository import CBBaseRepository


class CBCardRepository(CardRepository, CBBaseRepository[SomeCard, CBCard]):
    """Couchbase repository for the Card entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeCard] = Card,
        persistence_type: type[CBCard] = CBCard,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type
