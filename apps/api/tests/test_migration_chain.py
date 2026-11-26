"""Shape of the real Alembic revision graph: one linear chain with a single head."""

from __future__ import annotations

from migration_chain import forks, heads


def test_alembic_has_a_single_head() -> None:
    """Happy path: the migration chain resolves to exactly one head."""
    found = heads()

    assert len(found) == 1, f"expected one Alembic head, got {found}"


def test_no_revision_has_two_children() -> None:
    """Negative path: a fork is reported with the revision both branches grew from."""
    found_forks = forks()

    assert not found_forks, f"migration chain forks; these revisions each have several children: {found_forks}"
