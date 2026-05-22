"""Couchbase repository for Post."""

from typing import Any

from ....application.repositories.post_repository import PostRepository, SomePost
from ....domain.models.post import Post
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_post import CBPost
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBPostRepository(PostRepository, CBBaseRepository[SomePost, CBPost]):
    """Couchbase repository for the Post entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomePost] = Post,
        persistence_type: type[CBPost] = CBPost,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_channel_between(
        self,
        channel: str,
        start: float = 0.0,
        end: float = 999999999999.9,
        conversation_id: str | None = None,
    ) -> list[SomePost]:
        q, params = self._build_query(channel, start, end, conversation_id)
        items = self.repo.get_by_query(q, params)
        return [self.init_entity_valid_fields(item) for item in items]

    def _build_query(
        self,
        channel: str,
        start: float,
        end: float,
        conversation_id: str | None,
    ) -> tuple[str, dict[str, Any]]:
        b = bucket_ident(self.repo.bucket)
        clauses = [
            "type = $type",
            "$channel IN channels",
            "createdAt BETWEEN $start AND $end",
        ]
        params: dict[str, Any] = {
            "type": CBPost.type,
            "channel": channel,
            "start": start,
            "end": end,
        }
        if conversation_id is not None:
            clauses.append("conversationId = $conversationId")
            params["conversationId"] = conversation_id
        q = (
            f"SELECT {b}.*, META().id, META().xattrs._sync.rev AS _rev "
            f"FROM {b} "
            f"USE KEYS (SELECT RAW META().id "
            f"FROM {b} "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY createdAt);"
        )
        return q, params
