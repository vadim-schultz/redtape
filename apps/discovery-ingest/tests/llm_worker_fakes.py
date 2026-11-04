"""Fakes for the llm_extract worker tests: a machine API with the staging routes and a scripted model."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

import httpx
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.errors import LlmError

from extract_fakes import ARTIFACT_ID, PAGE_URL, ExtractApi, extract_task
from llm_fakes import taxonomy

if TYPE_CHECKING:
    from discovery_ingest.worker.llm_runtime import LlmResources

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
RUN_NEURONS = 800.0
PAGE_HTML = (
    "<html lang='de'><body><main><h1>Wohnsitz anmelden</h1>"
    "<p>Zur Anmeldung Ihres Wohnsitzes bringen Sie bitte Ihren Reisepass und die Meldebescheinigung zum Termin mit.</p>"
    "<p>Die Wohnungsgeberbestaetigung legen Sie ebenfalls vor, damit die Behoerde Ihre neue Adresse pruefen kann.</p>"
    "<p>Nach der Anmeldung erhalten Sie eine Meldebescheinigung, die Sie fuer weitere Antraege benoetigen.</p>"
    "</main></body></html>"
)
SHELL_HTML = "<html lang='de'><body><div id='app'></div></body></html>"


def answer(
    *documents: dict[str, str], page_kind: str = "service", dependencies: Sequence[dict[str, str]] = ()
) -> dict[str, Any]:
    """A model answer that tags the page ``home-and-housing`` and lists ``documents`` and ``dependencies``."""
    return {
        "page_kind": page_kind,
        "category_codes": ["home-and-housing"],
        "documents": list(documents),
        "dependencies": list(dependencies),
    }


def doc(name: str, role: str, quote: str) -> dict[str, str]:
    """One document item; the quote must occur on :data:`PAGE_HTML` to survive grounding."""
    return {"name": name, "role": role, "quote": quote}


PASS_DOC = doc("Reisepass", "required", "Ihren Reisepass")
CERT_DOC = doc("Meldebescheinigung", "issued", "erhalten Sie eine Meldebescheinigung")
FORM_DOC = doc("Wohnungsgeberbestaetigung", "required", "Die Wohnungsgeberbestaetigung legen Sie ebenfalls vor")
SERVICE = answer(PASS_DOC, CERT_DOC)


class ScriptedLlm:
    """Returns or raises the next scripted outcome per call and records the messages of every call."""

    def __init__(
        self,
        *outcomes: dict[str, Any] | str | LlmError | Exception,
        usage: tuple[int | None, int | None] = (1000, 200),
        on_call: Callable[[int], None] | None = None,
    ):
        self.outcomes = list(outcomes)
        self.usage = usage
        self.on_call = on_call
        self.messages: list[Sequence[dict[str, str]]] = []

    def extract(self, messages: Sequence[dict[str, str]], json_schema: dict[str, Any], *, max_tokens: int) -> LlmResult:
        """Return the next outcome, or raise it when it is an error; the last one repeats when the script ends."""
        self.messages.append(messages)
        if self.on_call is not None:
            self.on_call(len(self.messages))
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        text = outcome if isinstance(outcome, str) else json.dumps(outcome)
        return LlmResult(text, self.usage[0], self.usage[1], MODEL)

    @property
    def calls(self) -> int:
        """How many times the model was called."""
        return len(self.messages)


def resources(llm: ScriptedLlm) -> LlmResources:
    """The worker's model resources with the canned vocabulary and the 70B model."""
    from discovery_ingest.worker.llm_runtime import LlmResources

    return LlmResources(llm, taxonomy(), MODEL)


def llm_task(*, artifact_id: uuid.UUID | None = ARTIFACT_ID, url: str = PAGE_URL) -> dict[str, object]:
    """A claimed ``llm_extract`` task for the stored snapshot."""
    return {**extract_task(artifact_id=artifact_id, input_key=None, url=url), "kind": "llm_extract"}


class LlmApi(ExtractApi):
    """An :class:`ExtractApi` that also serves edges and the taxonomy, bills neurons and records the post order."""

    def __init__(self, tasks: list[dict[str, object]], html: str = PAGE_HTML) -> None:
        super().__init__(tasks, html.encode(), "text/html; charset=utf-8")
        self.ledger_remaining = 9000.0
        self.unknown_codes = 0
        self.taxonomy_status = 200
        self.edge_status = 200
        self.edge_detail = ""
        self.mention_status = 200
        self.mention_detail = ""
        self.posts: list[str] = []
        self.edge_posts: list[list[dict[str, Any]]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Serve edges and the taxonomy here; everything else as :class:`ExtractApi`."""
        path = request.url.path
        if path.endswith("/candidates/edges"):
            return self._edges(request)
        if path.endswith("/taxonomy"):
            return httpx.Response(self.taxonomy_status, json=taxonomy().model_dump(mode="json"))
        return super().handler(request)

    def _mentions(self, request: httpx.Request) -> httpx.Response:
        self.posts.append("mentions")
        if self.mention_status >= 400:
            return httpx.Response(self.mention_status, text=self.mention_detail)
        reply = super()._mentions(request)
        return httpx.Response(200, json={**reply.json(), "unknown_codes": self.unknown_codes})

    def _edges(self, request: httpx.Request) -> httpx.Response:
        self.posts.append("edges")
        if self.edge_status >= 400:
            return httpx.Response(self.edge_status, text=self.edge_detail)
        items = json.loads(request.content)["items"]
        self.edge_posts.append(items)
        counts = {"edges_created": len(items), "edges_updated": 0, "edges_skipped": 0, "skipped": []}
        return httpx.Response(200, json=counts)

    def _row(self) -> dict[str, object]:
        row = super()._row()
        return {**row, "resource": "neurons", "cap": 9500, "used": 9500 - (self.ledger_remaining or 0.0)}

    def mention_titles(self) -> list[str]:
        """The German titles of every mention posted, in order."""
        return [item["title_i18n"]["de"] for post in self.mention_posts for item in post]
