"""Mapping grounded extractions to mention and edge items."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from discovery_ingest.edges import EdgeItem
from discovery_ingest.extract.llm.ground_state import Diagnostics, Grounded
from discovery_ingest.extract.llm.mapping import MappingContext, to_items
from discovery_ingest.extract.llm.schema import DependencyItem, DocumentItem
from discovery_ingest.mentions import MentionItem, MentionsRequest
from pydantic import ValidationError

SERVICE_ID = UUID("00000000-0000-0000-0000-000000000001")
ARTIFACT_ID = UUID("00000000-0000-0000-0000-000000000002")
VERSION = "ext-1+clean-1+tax:abcdef12"
ISSUED_QUOTE = "Sie erhalten eine Meldebescheinigung."


def ctx(language: str | None = "de") -> MappingContext:
    return MappingContext(SERVICE_ID, ARTIFACT_ID, language, VERSION)


def doc(name: str, role: str = "required", quote: str | None = None, **extra: Any) -> DocumentItem:
    return DocumentItem.model_validate({"name": name, "role": role, "quote": quote or f"{name} mitbringen", **extra})


def dep(parent: str, requires: str, **extra: Any) -> DependencyItem:
    return DependencyItem.model_validate({"parent": parent, "requires": requires, "quote": "Zeile", **extra})


def grounded(
    documents: list[DocumentItem],
    dependencies: list[DependencyItem] | None = None,
    domains: tuple[str, ...] = (),
    situations: tuple[str, ...] = (),
) -> Grounded:
    diagnostics = Diagnostics("service", {}, 0, 0)
    return Grounded(tuple(documents), tuple(dependencies or ()), domains, situations, diagnostics)


ISSUED = doc("Meldebescheinigung", "issued", ISSUED_QUOTE)


def test_documents_become_mentions_with_source_field_llm_the_page_codes_and_the_extractor_version() -> None:
    document = doc("Personalausweis", url="https://portal.example/a", condition="bei Zuzug", is_optional=True)
    mentions, edges = to_items(grounded([document], domains=("housing",), situations=("moving-house",)), ctx())
    assert edges == []
    assert mentions == [
        MentionItem(
            catalogue_service_id=SERVICE_ID,
            artifact_id=ARTIFACT_ID,
            title_i18n={"de": "Personalausweis"},
            role="required",
            excerpt="Personalausweis mitbringen",
            source_field="llm",
            extractor="llm",
            extractor_version=VERSION,
            official_url="https://portal.example/a",
            condition="bei Zuzug",
            is_optional=True,
            domain_codes=["housing"],
            situation_codes=["moving-house"],
        )
    ]


def test_an_empty_page_maps_to_nothing() -> None:
    assert to_items(grounded([]), ctx()) == ([], [])


@pytest.mark.parametrize(("language", "expected"), [("en", "en"), (None, "de"), ("", "de")])
def test_the_title_language_comes_from_the_page_and_defaults_to_de(language: str | None, expected: str) -> None:
    mentions, _ = to_items(grounded([doc("Personalausweis")]), ctx(language))
    assert list(mentions[0].title_i18n) == [expected]


def test_the_staged_items_serialise_to_the_route_shape() -> None:
    mentions, edges = to_items(grounded([ISSUED, doc("Personalausweis")]), ctx())
    body = MentionsRequest(items=mentions).model_dump(mode="json")
    assert body["items"][0]["role"] == "issued"
    assert {"condition", "is_optional", "domain_codes", "situation_codes"} <= set(body["items"][0])
    assert set(edges[0].model_dump(mode="json")) == {
        "catalogue_service_id",
        "parent_title_i18n",
        "required_title_i18n",
        "basis",
        "condition",
        "is_optional",
        "excerpt",
        "extractor",
        "extractor_version",
    }


def test_the_item_types_reject_what_the_routes_reject() -> None:
    with pytest.raises(ValidationError):
        MentionItem(
            catalogue_service_id=SERVICE_ID,
            title_i18n={"de": "A"},
            role="required",
            excerpt="A",
            source_field="llm",
            extractor="llm",
            extractor_version=VERSION,
            domain_codes=["a", "b", "c"],
        )
    with pytest.raises(ValidationError):
        EdgeItem(
            catalogue_service_id=SERVICE_ID,
            parent_title_i18n={"de": "A"},
            required_title_i18n={"de": "B"},
            basis="explicit",
            excerpt="",
            extractor="llm",
            extractor_version=VERSION,
        )


def test_a_dependency_becomes_an_explicit_edge() -> None:
    documents = [ISSUED, doc("Personalausweis")]
    _, edges = to_items(grounded(documents, [dep("Meldebescheinigung", "Personalausweis", condition="ab 16")]), ctx())
    assert edges == [
        EdgeItem(
            catalogue_service_id=SERVICE_ID,
            parent_title_i18n={"de": "Meldebescheinigung"},
            required_title_i18n={"de": "Personalausweis"},
            basis="explicit",
            condition="ab 16",
            is_optional=None,
            excerpt="Zeile",
            extractor="llm",
            extractor_version=VERSION,
        )
    ]


def test_a_page_with_exactly_one_issued_document_derives_edges_to_every_required_document() -> None:
    documents = [
        ISSUED,
        doc("Personalausweis"),
        doc("Wohnungsgeberbestätigung", condition="bei Miete"),
        doc("Antrag", "form"),
    ]
    _, edges = to_items(grounded(documents), ctx())
    assert [(e.parent_title_i18n["de"], e.required_title_i18n["de"]) for e in edges] == [
        ("Meldebescheinigung", "Personalausweis"),
        ("Meldebescheinigung", "Wohnungsgeberbestätigung"),
    ]
    assert {e.basis for e in edges} == {"derived_single_issued"}
    assert {e.excerpt for e in edges} == {ISSUED_QUOTE}
    assert [e.condition for e in edges] == [None, "bei Miete"]


@pytest.mark.parametrize(
    "documents",
    [
        [ISSUED, doc("Reisepass", "issued", "Reisepass erhalten"), doc("Personalausweis")],
        [doc("Personalausweis"), doc("Antrag", "form")],
    ],
    ids=["two-issued", "no-issued"],
)
def test_a_page_without_exactly_one_issued_document_derives_no_edges(documents: list[DocumentItem]) -> None:
    assert to_items(grounded(documents), ctx())[1] == []


def test_an_explicit_edge_wins_over_a_derived_one_for_the_same_pair() -> None:
    documents = [ISSUED, doc("Personalausweis"), doc("Wohnungsgeberbestätigung")]
    _, edges = to_items(grounded(documents, [dep("meldebescheinigung", "PERSONALAUSWEIS")]), ctx())
    assert [(e.required_title_i18n["de"], e.basis) for e in edges] == [
        ("PERSONALAUSWEIS", "explicit"),
        ("Wohnungsgeberbestätigung", "derived_single_issued"),
    ]


def test_a_required_document_with_the_issued_documents_own_name_gets_no_self_edge() -> None:
    documents = [doc("Personalausweis", "issued", "Sie erhalten einen Personalausweis."), doc("Personalausweis")]
    assert to_items(grounded(documents), ctx())[1] == []
