"""Couchbase repository for Message."""

from typing import Any, Generic, Type

from arrow import Arrow

from ....application.repositories.message_repository import (
    MessageRepository,
    SomeMessage,
)
from ....domain.models.message import Message
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_conversation import CBMessage
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBMessageRepository(
    CBBaseRepository[SomeMessage, CBMessage],
    MessageRepository,
    Generic[SomeMessage],
):
    """Couchbase repository for the Message entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeMessage] = Message,
        persistence_type: type[CBMessage] = CBMessage,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type: Type[SomeMessage] = entity_type

    def get_for_owner_between(
        self,
        owner: str,
        start: Arrow,
        end: Arrow,
        subtype: int | None = None,
        condition: int | None = None,
    ) -> list[SomeMessage]:
        b = bucket_ident(self.repo.bucket)
        clauses = [
            "type = $type",
            "owner = $owner",
            "createdAt BETWEEN $start AND $end",
        ]
        params: dict[str, Any] = {
            "type": CBMessage.type,
            "owner": owner,
            "start": start.timestamp(),
            "end": end.timestamp(),
        }
        if subtype is not None:
            clauses.append("subtype = $subtype")
            params["subtype"] = subtype
        if condition is not None:
            clauses.append("condition = $condition")
            params["condition"] = condition
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY createdAt"
        )
        return [
            self.init_entity_valid_fields(item)
            for item in self.repo.get_by_query(q, params)
        ]
