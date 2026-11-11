"""Deletes of replaced translation objects that wait for the database commit that made them garbage."""

from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.features.translation.store import TranslationStore
from app.shared.object_store import ObjectStore, ObjectStoreError

logger = logging.getLogger(__name__)


class AfterCommitDeletes:
    """Collect keys and delete them once the session commits; a rollback forgets them, a failed delete is logged.

    The replaced object is only garbage after the index row has moved. Deleting it earlier could leave a row that
    points at nothing; an orphan left by a failed delete is unreferenced, bounded and harmless.
    """

    def __init__(self, session: Session, store: ObjectStore | None) -> None:
        """Watch ``session`` and delete through ``store`` after its commits."""
        self._store = store
        self._keys: list[str] = []
        event.listen(session, "after_commit", self._run)
        event.listen(session, "after_rollback", self._drop)

    def add(self, key: str) -> None:
        """Schedule ``key`` for deletion after the next commit."""
        self._keys.append(key)

    def _run(self, _: Session) -> None:
        keys, self._keys = self._keys, []
        for key in keys:
            self._delete(key)

    def _drop(self, _: Session) -> None:
        self._keys.clear()

    def _delete(self, key: str) -> None:
        try:
            TranslationStore(self._store).delete(key)
        except ObjectStoreError:
            logger.warning("could not delete the replaced translation object %s", key, exc_info=True)
