"""The authorization decision for one request, driven by ``POLICY`` (ADR 0007).

Invariants:

* Deny by default: an unknown module or op is 403, and a column the caller does
  not hold a role for gives no verdict at all.
* Scope before role (D-06): a caller outside the record's scope gets 404, the
  same text a missing record gets; 403 appears only inside the caller's own
  scope. A caller holding several roles gets the best verdict of their columns
  (D-07).
* Nothing is shared between requests: ``Access`` is built per request from the
  verified ``Principal`` and keeps its own Participant reads.

Decision order for one request (see ``Access._open``): role predicate, then the
scope-none rule, then the scope predicate, then the best verdict across columns.
A predicate that needs the record is deferred until the handler passes the
record to ``check_record`` or the list to ``scope_list``. A handler that skips
both fails open for deferred columns; ``tests/test_policy_matrix.py`` is what
catches a router that does.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from collections.abc import Iterable
from typing import Any

from fastapi import Depends, HTTPException, Request

from openwellness_core.domain.exceptions.domain_exception import (
    EntityNotFoundException,
)

from ..common.handlers import stamp_audit
from ..deps.principal import Principal, get_principal
from ..errors.responses import build_error
from .policy import OPS, POLICY, Row

logger = logging.getLogger(__name__)

_NO_RECORD: Any = object()
_DEFER = None  # a predicate result meaning "needs the record"
# Coach writes that also require the record owner's Participant to be in study.
_COACH_WRITE_CHECKED = frozenset({"patch", "delete", "undelete"})


class Verdict(IntEnum):
    """Higher wins across columns (D-07)."""

    NOT_FOUND = 0
    FORBIDDEN = 1
    ALLOW = 2


def _archived(entity: Any) -> bool:
    """One place that decides an entity is archived (OQ3)."""
    return getattr(entity, "deleted_at", None) is not None


class authorize:  # noqa: N801 - a callable class so tests can read .module and .op
    """FastAPI dependency: ``Depends(authorize("weight", "list"))`` gives an ``Access``."""

    def __init__(self, module: str, op: str) -> None:
        self.module = module
        self.op = op

    def __call__(
        self, request: Request, principal: Principal = Depends(get_principal)
    ) -> Access:
        row = POLICY.get(self.module)
        if row is None or self.op not in OPS:
            logger.error(
                "authz: no policy: principal=%s module=%s op=%s",
                principal.id,
                self.module,
                self.op,
            )
            raise _forbidden()
        access = Access(request, principal, self.module, self.op, row)
        access._open()
        return access


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=build_error(403, "PERMISSION_DENIED", "Permission denied."),
    )


class Access:
    """What one request may do. Built by ``authorize``, never shared."""

    def __init__(
        self, request: Request, principal: Principal, module: str, op: str, row: Row
    ) -> None:
        self._request = request
        self.principal = principal
        self._module = module
        self._op = op
        self._row = row
        self._path: dict[str, Any] = request.path_params
        self._participants: dict[str, Any] = {}
        self._columns = ["self"]
        if "coach" in principal.roles:
            self._columns.append("coach")
        if principal.is_admin:
            self._columns.append("admin")
        self._best = Verdict.NOT_FOUND
        self._deferred: list[str] = []
        self._allowed = False

    # -- Participant reads, cached for this request ------------------------ #

    def _participant(self, pid: Any) -> Any:
        if not pid:
            return None
        if pid not in self._participants:
            repo = self._request.app.state.container.repositories.participant()
            try:
                self._participants[pid] = repo.get_by_id(pid)
            except EntityNotFoundException:
                self._participants[pid] = None
        return self._participants[pid]

    def _study_of(self, pid: Any) -> str:
        """The study of a Participant; "" fails closed (missing, archived, empty)."""
        participant = self._participant(pid)
        if participant is None or _archived(participant):
            return ""
        return getattr(participant, "study_id", "") or ""

    # -- Predicates --------------------------------------------------------- #

    def _self_pred(self, scope: str, record: Any) -> bool | None:
        claim = self.principal.participant or ""
        seg = self._path
        if scope == "self-user":
            user = seg.get("user")
            return True if user is None else user == self.principal.id
        if not claim:
            return False
        if scope == "self-owner":
            return seg.get("user") == claim
        if scope == "self-participant":
            participant = seg.get("participant")
            return True if participant is None else participant == claim
        if scope == "self-study":
            study = seg.get("study")
            if study is not None:
                own = self._study_of(claim)
                return bool(own) and study == own
            if record is _NO_RECORD:
                return True if self._op in ("list", "create") else _DEFER
            own = self._study_of(claim)
            return bool(own) and getattr(record, "id", None) == own
        if scope in ("self-device", "self-fitbit"):
            if record is _NO_RECORD:
                if self._op == "list":
                    return _DEFER if "list" in self._row.self_ops else True
                return True if self._op == "create" else _DEFER
            return getattr(record, "participant_id", None) == claim
        if scope == "self-member-group":
            if seg.get("user") != claim:
                return False
            if record is _NO_RECORD:
                return True if self._op in ("list", "create") else _DEFER
            members = getattr(record, "participant_ids", None) or []
            return claim in members and not _archived(record)
        if scope == "self-member-conversation":
            if record is _NO_RECORD:
                return True if self._op == "create" else _DEFER
            # shortcut: the domain Conversation carries no channels, so participants
            # match nothing; the stored membership link is Phase 6 (ADR 0007 Phase 2
            # amendment).
            return False
        return False

    def _coach_pred(self, record: Any) -> bool | None:
        studies = self.principal.coach_studies

        def held(study_id: Any) -> bool:
            return bool(study_id) and study_id in studies

        study = self._path.get("study")
        if study is not None:
            return held(study)
        binding = self._row.binding
        if binding is None:  # the study row with no segment: list, :lookup, create
            if record is _NO_RECORD:
                return True if self._op == "create" else _DEFER
            return held(getattr(record, "id", ""))
        if binding == "membership":
            if record is _NO_RECORD:
                return True if self._op == "create" else _DEFER
            return held(getattr(record, "study_id", ""))
        if binding == "participant":
            if record is _NO_RECORD:
                if self._op == "create":
                    return held(self._study_of(self._path.get("user")))
                return _DEFER
            if not held(getattr(record, "study_id", "")):
                return False
            if self._op in _COACH_WRITE_CHECKED and self._op in self._row.coach_ops:
                return held(self._study_of(getattr(record, "owner", "")))
            return True
        return False

    # -- Verdicts ------------------------------------------------------------ #

    def _verdict(self, column: str, record: Any = _NO_RECORD) -> Verdict | None:
        row = self._row
        if column == "admin":
            return Verdict.ALLOW if self._op in row.admin_ops else Verdict.FORBIDDEN
        is_self = column == "self"
        scope = row.self_scope if is_self else row.coach_scope
        if scope is None:
            return Verdict.FORBIDDEN
        held = (
            self._self_pred(scope, record) if is_self else self._coach_pred(record)
        )
        if held is _DEFER:
            return None
        if not held:
            return Verdict.NOT_FOUND
        cell = row.self_ops if is_self else row.coach_ops
        return Verdict.ALLOW if self._op in cell else Verdict.FORBIDDEN

    def _open(self) -> None:
        verdicts: list[Verdict] = []
        for column in self._columns:
            verdict = self._verdict(column)
            if verdict is None:
                self._deferred.append(column)
            else:
                verdicts.append(verdict)
        self._best = max(verdicts, default=Verdict.NOT_FOUND)
        if self._best is Verdict.ALLOW:
            self._allowed = True
        elif not self._deferred:
            self._deny(self._best)

    # -- Denials -------------------------------------------------------------- #

    def _not_found_text(self, name: str | None) -> str:
        """Same text ``not_found``/``check_parent`` raise, derived from the URL."""
        segs = [s for s in self._request.url.path.split("/") if s]
        if segs and segs[0] == "v1":
            segs = segs[1:]
        if segs:
            segs[-1] = segs[-1].split(":", 1)[0]
        if len(segs) % 2 == 0:
            collection, id_, parent = segs[-2], segs[-1], segs[:-2]
        else:
            collection, id_, parent = segs[-1], None, segs[:-1]
        id_ = name or id_
        text = f"{collection}/{id_}" if id_ else collection
        text += " not found"
        return f"{text} for {'/'.join(parent)}" if parent else text

    def _deny(self, verdict: Verdict, *, name: str | None = None) -> Any:
        logger.info(
            "authz denied: principal=%s module=%s op=%s status=%s",
            self.principal.id,
            self._module,
            self._op,
            403 if verdict is Verdict.FORBIDDEN else 404,
        )
        if verdict is Verdict.FORBIDDEN:
            raise _forbidden()
        raise EntityNotFoundException(self._not_found_text(name))

    # -- What handlers call ------------------------------------------------------ #

    def scope_list(self, items: list[Any]) -> list[Any]:
        """Keep the records the caller may see (D-08). Call before ``filter=`` and paging."""
        if self._allowed:
            return items
        kept = [
            item
            for item in items
            if any(self._verdict(c, item) is Verdict.ALLOW for c in self._deferred)
        ]
        if "{user}" in self._row.route and items and not kept:
            self._deny(Verdict.NOT_FOUND)
        return kept

    def check_record(self, entity: Any, *, name: str | None = None) -> Any:
        """Return ``entity`` if the caller may act on it, else raise 403 or 404.

        ``name`` is for a route whose id is in the body, so the URL cannot supply
        it: the 404 then reads ``{collection}/{name} not found``.
        """
        if self._allowed:
            return entity
        best = self._best
        for column in self._deferred:
            verdict = self._verdict(column, entity)
            assert verdict is not None  # a record was supplied
            best = max(best, verdict)
        if best is not Verdict.ALLOW:
            self._deny(best, name=name)
        return entity

    def stamp_create(
        self, payload: dict[str, Any], *, parent_id: str | None
    ) -> dict[str, Any]:
        """Bind a new record to a study server-side, then stamp owner and audit (D-16)."""
        binding = self._row.binding
        if binding is None:
            raise ValueError(
                f"stamp_create: {self._module} has no study binding; "
                "its router keeps its own create"
            )
        supplied = payload.get("study_id") or ""
        if binding == "participant":
            study = self._study_of(parent_id)
        elif binding == "study":
            study = parent_id or ""
        else:  # membership: no owner to derive from, the caller names the study
            study = supplied
            if study and not self.principal.is_admin:
                if study not in self.principal.coach_studies:
                    study = ""
        if not study or (supplied and supplied != study):
            self._deny(Verdict.NOT_FOUND)
        payload["study_id"] = study
        return stamp_audit(payload, parent_id=parent_id, principal=self.principal)

    def check_members(self, participant_ids: Iterable[str]) -> None:
        """A coach's group may only hold participants of their studies (A-09-2)."""
        if self.principal.is_admin:
            return
        studies = self.principal.coach_studies
        for pid in participant_ids:
            study = self._study_of(pid)
            if not study or study not in studies:
                self._deny(Verdict.NOT_FOUND)
