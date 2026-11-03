from __future__ import annotations

import ast
import inspect
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest
from app.features.locations.openplz.client import OpenPLZClient, OpenPLZPayloadError, _RateLimiter
from app.features.locations.openplz.models import OpenPLZDistrict, OpenPLZFederalState


class _Handler(BaseHTTPRequestHandler):
    """Serves whatever `responses` maps the request path+query to."""

    responses: dict[str, object] = {}

    def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
        body = self.responses.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        payload = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


@pytest.fixture
def server():
    _Handler.responses = {}
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        thread.join()


def _client(server: HTTPServer) -> OpenPLZClient:
    host, port = server.server_address
    return OpenPLZClient(base_url=f"http://{host}:{port}", rate_limit_rps=1000.0)


def test_paged_list_payload_yields_models(server: HTTPServer) -> None:
    _Handler.responses = {
        "/de/FederalStates/14/Districts?page=1&pageSize=50": [
            {"key": "14612", "name": "Dresden", "type": "Kreisfreie Stadt"}
        ],
        "/de/FederalStates/14/Districts?page=2&pageSize=50": [],
    }
    client = _client(server)

    items = list(client.districts("14"))

    assert items == [OpenPLZDistrict(key="14612", name="Dresden", type="Kreisfreie Stadt")]


def test_paged_items_envelope_yields_models(server: HTTPServer) -> None:
    _Handler.responses = {
        "/de/FederalStates/14/Districts?page=1&pageSize=50": {
            "items": [{"key": "14612", "name": "Dresden", "type": "Kreisfreie Stadt"}]
        },
        "/de/FederalStates/14/Districts?page=2&pageSize=50": {"items": []},
    }
    client = _client(server)

    items = list(client.districts("14"))

    assert [item.key for item in items] == ["14612"]


def test_paged_data_envelope_is_the_fallback(server: HTTPServer) -> None:
    _Handler.responses = {
        "/de/FederalStates/14/Districts?page=1&pageSize=50": {
            "data": [{"key": "14612", "name": "Dresden", "type": "Kreisfreie Stadt"}]
        },
        "/de/FederalStates/14/Districts?page=2&pageSize=50": {"data": []},
    }
    client = _client(server)

    items = list(client.districts("14"))

    assert [item.key for item in items] == ["14612"]


def test_empty_page_stops_iteration(server: HTTPServer) -> None:
    _Handler.responses = {"/de/FederalStates/14/Districts?page=1&pageSize=50": []}
    client = _client(server)

    items = list(client.districts("14"))

    assert items == []


def test_max_pages_stops_iteration(server: HTTPServer) -> None:
    _Handler.responses = {
        "/de/FederalStates/14/Districts?page=1&pageSize=50": [{"key": "1", "name": "A", "type": "Landkreis"}],
        "/de/FederalStates/14/Districts?page=2&pageSize=50": [{"key": "2", "name": "B", "type": "Landkreis"}],
    }
    client = _client(server)

    items = list(client._paged("FederalStates/14/Districts", OpenPLZDistrict, max_pages=1))

    assert [item.key for item in items] == ["1"]


def test_rate_limiter_rejects_non_positive_rps() -> None:
    with pytest.raises(ValueError, match="rps"):
        _RateLimiter(0)


def test_http_error_carries_status_url_and_truncated_body(server: HTTPServer) -> None:
    from app.features.locations.openplz.client import OpenPLZHTTPError

    client = _client(server)

    with pytest.raises(OpenPLZHTTPError) as exc_info:
        client.federal_states()

    err = exc_info.value
    assert err.status == 404
    assert err.url.endswith("/de/FederalStates")
    assert "not found" in err.body


def test_unexpected_payload_type_raises_payload_error_with_endpoint(server: HTTPServer) -> None:
    _Handler.responses = {"/de/FederalStates/14/Districts?page=1&pageSize=50": "not-a-list-or-dict"}
    client = _client(server)

    with pytest.raises(OpenPLZPayloadError) as exc_info:
        list(client.districts("14"))

    assert exc_info.value.endpoint == "FederalStates/14/Districts"
    assert exc_info.value.page == 1


def test_item_missing_required_key_raises_payload_error(server: HTTPServer) -> None:
    _Handler.responses = {
        # OpenPLZDistrict requires "type"; this item is missing it.
        "/de/FederalStates/14/Districts?page=1&pageSize=50": [{"key": "14612", "name": "Dresden"}]
    }
    client = _client(server)

    with pytest.raises(OpenPLZPayloadError) as exc_info:
        list(client.districts("14"))

    assert exc_info.value.endpoint == "FederalStates/14/Districts"
    assert exc_info.value.page == 1


def test_client_has_no_any_in_its_public_signatures() -> None:
    from app.features.locations.openplz import client as client_module

    source = inspect.getsource(client_module)
    tree = ast.parse(source)

    any_names = {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if (isinstance(node, ast.Name) and node.id == "Any") or (isinstance(node, ast.Attribute) and node.attr == "Any")
    }
    assert any_names == set()


def test_importer_uses_typed_endpoint_methods() -> None:
    from tests.test_import_openplz_incremental import _FakeClient

    fake = _FakeClient({"states": [], "districts": {}, "municipalities": {}, "localities": {}})

    assert not hasattr(fake, "get_json")
    assert not hasattr(fake, "iter_paged")
    assert hasattr(fake, "federal_states")
    assert hasattr(fake, "districts")
    assert hasattr(fake, "municipalities")
    assert hasattr(fake, "localities")


def test_federal_states_returns_typed_models(server: HTTPServer) -> None:
    _Handler.responses = {"/de/FederalStates": [{"key": "14", "name": "Sachsen"}]}
    client = _client(server)

    states = client.federal_states()

    assert states == [OpenPLZFederalState(key="14", name="Sachsen")]
