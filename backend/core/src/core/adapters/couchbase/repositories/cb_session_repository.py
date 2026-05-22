"""Couchbase repository for Session."""

from typing import Any, List, Type, TypeVar

from ....application.repositories.session_repository import SessionRepository
from ....domain.models.session import Session
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_session import CBSession
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository

SomeSession = TypeVar("SomeSession", bound=Session)


class CBSessionRepository(
    SessionRepository[SomeSession], CBBaseRepository[SomeSession, CBSession]
):
    """Couchbase repository for the Session entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeSession] = Session,
        persistence_type: type[CBSession] = CBSession,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def fetch_sessions_in_range(
        self,
        owner: str,
        start: float = 0.0,
        end: float = 9999999999999.9,
        require_session_type: bool = False,
        session_type: int | None = None,
    ) -> List[SomeSession]:
        b = bucket_ident(self.repo.bucket)
        clauses, params = self._base_clauses(owner, start, end)
        clauses.extend(self._session_type_clauses(require_session_type, session_type, params))
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE {' AND '.join(clauses)} "
            f"ORDER BY timeStartInMS, createdAt"
        )
        return self.get_by_query(q, params)

    def count_sessions_in_range(
        self,
        owner: str,
        start: float = 0.0,
        end: float = 9999999999999.9,
        require_session_type: bool = False,
        session_type: int | None = None,
    ) -> int:
        b = bucket_ident(self.repo.bucket)
        clauses, params = self._base_clauses(owner, start, end)
        clauses.extend(self._session_type_clauses(require_session_type, session_type, params))
        q = (
            f"SELECT COUNT(*) AS num "
            f"FROM {b} "
            f"WHERE {' AND '.join(clauses)}"
        )
        return self.execute_query(q, params)[0]["num"]

    def _base_clauses(
        self, owner: str, start: float, end: float
    ) -> tuple[list[str], dict[str, Any]]:
        params: dict[str, Any] = {
            "type": CBSession.type,
            "owner": owner,
            "start": start,
            "end": end,
        }
        clauses = [
            "type = $type",
            "owner = $owner",
            "timeStartInMS BETWEEN $start AND $end",
        ]
        return clauses, params

    def _session_type_clauses(
        self,
        require_session_type: bool,
        session_type: int | None,
        params: dict[str, Any],
    ) -> list[str]:
        if not require_session_type:
            return []
        if session_type is not None:
            params["sessionType"] = session_type
            return ["sessionType = $sessionType"]
        return ["sessionType IS MISSING"]
