"""Couchbase repository for Conversations."""

from typing import Any

from ....application.repositories.conversation_repository import (
    ConversationRepository,
    SomeConversation,
)
from ....domain.models.conversation import Conversation
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_conversation import CBConversation
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBConversationRepository(
    ConversationRepository, CBBaseRepository[SomeConversation, CBConversation]
):
    """Couchbase repository for the Conversation entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeConversation] = Conversation,
        persistence_type: type[CBConversation] = CBConversation,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_filters(
        self, filters: list[Conversation.Filter]
    ) -> list[SomeConversation]:
        q, params = self._build_query(filters)
        items = self.repo.get_by_query(q, params)
        return [self.init_entity_valid_fields(item) for item in items]

    def _build_query(
        self, filters: list[Conversation.Filter]
    ) -> tuple[str, dict[str, Any]]:
        b = bucket_ident(self.repo.bucket)
        clauses = ["type = $type"]
        params: dict[str, Any] = {"type": CBConversation.type}
        for idx, f in enumerate(filters):
            clause, filter_params = f.to_n1ql(idx)
            if clause:
                clauses.append(clause)
                params.update(filter_params)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY kind, createdAt"
        )
        return q, params
