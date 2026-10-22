"""Shared paging and locale dependencies, and the controller parameter budget."""

from __future__ import annotations

import inspect

import pytest
from app.features.documents.controller import DocumentsController
from app.features.locations.controller import LocationsController
from app.features.suggestions.controller import SuggestionsController
from app.features.taxonomy.controller import TaxonomyController
from app.shared.locale import ResolvedLocale, provide_resolved_locale
from app.shared.paging import PageParams, provide_page_params
from litestar import Litestar, get
from litestar.datastructures import State
from litestar.di import Provide
from litestar.testing import RequestFactory, TestClient

MAX_HANDLER_PARAMS = 3  # excluding self


@get("/page", sync_to_thread=False)
def _page(page: PageParams) -> dict[str, int]:
    return {"offset": page.offset, "limit": page.limit}


def _paging_client() -> TestClient[Litestar]:
    return TestClient(Litestar([_page], dependencies={"page": Provide(provide_page_params, sync_to_thread=False)}))


def test_page_params_default_to_offset_0_limit_20() -> None:
    assert _paging_client().get("/page").json() == {"offset": 0, "limit": 20}


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_page_params_reject_out_of_range_values(query: str) -> None:
    assert _paging_client().get(f"/page?{query}").status_code == 400


def _request(enabled: set[str] | None, locale: str | None):
    app = Litestar(state=State({"enabled_locale_codes": enabled} if enabled else {}))
    request = RequestFactory(app=app).get("/")
    if locale:
        request.scope["state"] = {"locale": locale}
    return request


def test_resolved_locale_reads_request_state_and_enabled_codes() -> None:
    resolved = provide_resolved_locale(_request({"de", "fr"}, "fr"))

    assert resolved == ResolvedLocale(code="fr", enabled=set({"de", "fr"}))


def test_resolved_locale_defaults_to_de_and_de_en() -> None:
    resolved = provide_resolved_locale(_request(None, None))

    assert resolved == ResolvedLocale(code="de", enabled=set({"de", "en"}))


# Handlers audited by chapter 4; `get_suggestion` (voting composition) and `get_matrix` keep 4 for now.
BUDGETED_HANDLERS = [
    (DocumentsController, "list_documents"),
    (DocumentsController, "get_document"),
    (SuggestionsController, "create"),
    (SuggestionsController, "list_suggestions"),
    (LocationsController, "list_countries"),
    (LocationsController, "list_states"),
    (LocationsController, "list_districts"),
    (LocationsController, "list_cities"),
    (LocationsController, "list_localities"),
    (TaxonomyController, "list_domains"),
    (TaxonomyController, "list_life_situations"),
]


@pytest.mark.parametrize(("controller", "name"), BUDGETED_HANDLERS)
def test_handlers_take_at_most_three_parameters(controller: type, name: str) -> None:
    params = [p for p in inspect.signature(vars(controller)[name].fn).parameters if p != "self"]

    assert len(params) <= MAX_HANDLER_PARAMS, params
