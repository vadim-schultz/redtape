"""The code guard: a page that kept no document carries no domain or life-situation codes."""

from __future__ import annotations

import pytest

from test_extraction_grounding import doc, run

CODES = {"domain_codes": ["housing"], "situation_codes": ["moving-house"]}


def test_a_service_page_with_a_kept_document_keeps_its_codes() -> None:
    """guard · the happy path: documents and codes survive together."""
    grounded = run([doc("Personalausweis")], **CODES)
    assert (grounded.domain_codes, grounded.situation_codes) == (("housing",), ("moving-house",))


def test_a_service_page_that_kept_no_document_yields_no_codes() -> None:
    """guard · a page whose model answer held no documents has nothing the codes could attach to."""
    grounded = run([], **CODES)
    assert (grounded.documents, grounded.domain_codes, grounded.situation_codes) == ((), (), ())


def test_a_service_page_whose_documents_were_all_dropped_yields_no_codes() -> None:
    """guard · ble-kaese-lagerhaltung: only ``Bekanntmachung`` and ``Antragsformularen`` were returned, with codes."""
    grounded = run([doc("Bekanntmachung"), doc("Antragsformularen", role="form")], **CODES)
    assert grounded.documents == ()
    assert (grounded.domain_codes, grounded.situation_codes) == ((), ())
    assert grounded.diagnostics.dropped == {"generic_name": 2}


def test_one_surviving_document_among_dropped_ones_keeps_the_codes() -> None:
    """guard · negative: the guard looks at what is kept, not at what was returned."""
    grounded = run([doc("Bekanntmachung"), doc("Personalausweis")], **CODES)
    assert grounded.domain_codes == ("housing",)


@pytest.mark.parametrize("kind", ["login_or_error", "other"])
def test_a_page_of_a_non_procedure_kind_yields_no_codes_even_with_documents(kind: str) -> None:
    """guard · unchanged: the existing rule for pages that are not a procedure."""
    grounded = run([doc("Personalausweis")], page_kind=kind, **CODES)
    assert (grounded.domain_codes, grounded.situation_codes) == ((), ())
