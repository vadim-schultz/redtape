"""A unit's context reaches the Workers AI prompt and the estimate, and costs nothing when a unit has none (search-first C11)."""

from __future__ import annotations

import json

from discovery_ingest.translation.adapters.cloudflare_prompt import CONTEXT_RULE, build_messages
from discovery_ingest.translation.units import TranslationUnit

from translation_fakes import batch, unit


def test_a_unit_with_context_sends_it_beside_the_text_and_adds_the_rule() -> None:
    """prompt · the context is a read-only field of the unit and the system message says how to use it."""
    with_context = TranslationUnit("k", "Speichern", "", "key: common.save; English: Save")

    system, user = build_messages(batch(with_context), "Turkish")

    sent = json.loads(user["content"])["units"][0]
    assert sent["context"] == "key: common.save; English: Save" and CONTEXT_RULE in system["content"]


def test_a_unit_without_context_sends_no_field_and_no_rule() -> None:
    """prompt · document translation is unchanged: no context field, no context rule."""
    system, user = build_messages(batch(unit("k", "Antrag", "Text")), "Turkish")

    assert "context" not in json.loads(user["content"])["units"][0]
    assert CONTEXT_RULE not in system["content"]
