"""The source hash of a translation unit: what makes a stored translation stale."""

from __future__ import annotations

from app.features.translation.source_hash import source_hash


def test_the_hash_is_stable_and_changes_with_the_title_the_description_or_the_recipe() -> None:
    """source hash · stable for equal input, different for a changed title, description or recipe version."""
    base = source_hash("Kindergeldantrag", "Antrag auf Kindergeld", recipe_version="v1")

    assert base == source_hash("Kindergeldantrag", "Antrag auf Kindergeld", recipe_version="v1")
    assert len(base) == 64
    assert base != source_hash("Kindergeld", "Antrag auf Kindergeld", recipe_version="v1")
    assert base != source_hash("Kindergeldantrag", "Antrag auf Kindergeld.", recipe_version="v1")
    assert base != source_hash("Kindergeldantrag", "Antrag auf Kindergeld", recipe_version="v2")


def test_moving_text_between_title_and_description_changes_the_hash() -> None:
    """source hash · the fields are delimited, so shifting a word from title to description is a different unit."""
    assert source_hash("ab", "c", recipe_version="v1") != source_hash("a", "bc", recipe_version="v1")
