"""Read the real Alembic revision graph without a database, so tests can find its head and any fork."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from alembic.config import Config
from alembic.script import Script, ScriptDirectory

API_ROOT = Path(__file__).resolve().parent.parent


def script_directory() -> ScriptDirectory:
    """Load the migration chain from ``apps/api/alembic``."""
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def heads() -> tuple[str, ...]:
    """Return every head revision id of the chain."""
    return tuple(script_directory().get_heads())


def single_head() -> str:
    """Return the chain's only head id, or raise when the chain has none or several."""
    found = heads()
    if len(found) != 1:
        raise RuntimeError(f"expected one Alembic head, got {found}")
    return found[0]


def forks() -> dict[str, list[str]]:
    """Map each parent revision with several children to those children."""
    children: dict[str, list[str]] = defaultdict(list)
    for revision in script_directory().walk_revisions():
        for parent in _parents(revision):
            children[parent].append(revision.revision)
    return {parent: kids for parent, kids in children.items() if len(kids) > 1}


def _parents(revision: Script) -> tuple[str, ...]:
    """Return the parent revision ids of ``revision``, whether it is a plain or a merge revision."""
    down = revision.down_revision
    if down is None:
        return ()
    return down if isinstance(down, tuple) else (down,)
