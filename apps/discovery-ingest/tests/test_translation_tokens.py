"""Placeholder protection: each placeholder goes out as an opaque token and comes back as the placeholder it replaced (AZ04)."""

from __future__ import annotations

from discovery_ingest.translation import tokens


def test_protect_replaces_each_placeholder_by_a_numbered_token_and_keeps_the_rest_of_the_text() -> None:
    """Placeholders · a placeholder becomes ⟦n⟧ in order; the text around it and repeated names are untouched."""
    protected, found = tokens.protect("Von {total} bis {name}, {total} Stück")

    assert protected == "Von ⟦0⟧ bis ⟦1⟧, ⟦2⟧ Stück"
    assert found == ("{total}", "{name}", "{total}")
    assert "{" not in protected


def test_restore_puts_each_placeholder_back_where_its_token_was() -> None:
    """Placeholders · protect then restore returns the original text byte for byte."""
    text = "{count} von {total} (%(name)s, %d) {name}"
    protected, found = tokens.protect(text)

    assert tokens.restore(protected, found) == text


def test_a_token_the_translation_invented_is_left_as_it_is() -> None:
    """Placeholders · a token with no placeholder behind it stays in the text; the validators then see it."""
    assert tokens.restore("⟦0⟧ und ⟦7⟧", ("{name}",)) == "{name} und ⟦7⟧"


def test_a_text_without_placeholders_is_unchanged_by_protect_and_restore() -> None:
    """Placeholders · a text without placeholders passes through protect and restore unchanged."""
    protected, found = tokens.protect("Speichern und 2 Dokumente")

    assert (protected, found) == ("Speichern und 2 Dokumente", ())
    assert tokens.restore(protected, found) == "Speichern und 2 Dokumente"
